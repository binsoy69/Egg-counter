# Architecture Patterns

**Domain:** Raspberry Pi edge computer vision with remote web dashboard
**Researched:** 2026-03-19

## Recommended Architecture

A three-layer monolith running on a single Raspberry Pi 5, with a clear separation between the detection pipeline, application server, and data persistence. All three layers run as a single Python process (or at most two: detector + web server) on the Pi itself. There is no cloud backend; the Pi is the server.

```
                         +-------------------+
                         |   Phone Browser   |
                         |   (Dashboard UI)  |
                         +--------+----------+
                                  |
                              HTTPS / WSS
                          (Cloudflare Tunnel)
                                  |
+------------------------------------------------------------------+
|  Raspberry Pi 5                                                  |
|                                                                  |
|  +-----------+    +----------------+    +-------------------+    |
|  | USB       |    | Detection      |    | Web Server        |    |
|  | Camera    +--->+ Pipeline       +--->+ (FastAPI/Uvicorn) |    |
|  |           |    |                |    |                   |    |
|  +-----------+    | - Frame grab   |    | - REST API        |    |
|                   | - YOLO infer   |    | - WebSocket hub   |    |
|                   | - Tracker      |    | - Static files    |    |
|                   | - Classifier   |    |                   |    |
|                   +-------+--------+    +--------+----------+    |
|                           |                      |               |
|                           v                      v               |
|                   +-------+----------------------+----------+    |
|                   |          SQLite Database                 |    |
|                   |  - egg_events (timestamp, size, conf)    |    |
|                   |  - daily_summaries (date, counts)        |    |
|                   +------------------------------------------+    |
+------------------------------------------------------------------+
```

### Why a monolith on the Pi

A microservices split (separate detection service, separate API server, message queue between them) adds operational complexity with zero benefit at this scale. Under 100 eggs/day, single-digit FPS inference, one user -- a single Python process handles everything. The separation is at the code module level (clear boundaries), not at the process level.

### Component Boundaries

| Component | Responsibility | Communicates With | Technology |
|-----------|---------------|-------------------|------------|
| **Camera Capture** | Grab frames from USB camera at steady interval | Detection Pipeline (passes frames) | OpenCV VideoCapture |
| **Detection Pipeline** | Run YOLO inference, track objects across frames, classify egg size | Camera Capture (receives frames), Event Processor (emits detections) | Ultralytics YOLO, NCNN export |
| **Object Tracker** | Prevent double-counting by tracking egg identity across frames | Detection Pipeline (receives raw detections), Event Processor (emits unique egg events) | Built-in Ultralytics tracker or simple centroid tracker |
| **Event Processor** | Validate new egg events, persist to database, broadcast via WebSocket | Tracker (receives unique events), Database (writes), WebSocket Hub (broadcasts) | Python application logic |
| **SQLite Database** | Store egg detection events, daily aggregations, system state | Event Processor (writes), REST API (reads) | SQLite3 (stdlib) |
| **Web Server** | Serve REST API for historical data, WebSocket for real-time updates, static dashboard files | Database (reads), Browser (serves), Event Processor (receives broadcasts) | FastAPI + Uvicorn |
| **Dashboard UI** | Display counts, charts, trends; receive live updates | Web Server (WebSocket + REST) | Vanilla JS or lightweight framework (Preact/Alpine.js) |
| **Tunnel** | Expose Pi's local web server to the internet for remote phone access | Web Server (proxies to), Phone Browser (connects through) | Cloudflare Tunnel (cloudflared) |

### Data Flow

**Real-time detection flow (hot path):**

```
USB Camera
    |
    v  (raw frame, ~2-5 FPS)
Frame Grabber (OpenCV)
    |
    v  (numpy array, resized to 640x640)
YOLO Inference (NCNN export)
    |
    v  (list of bounding boxes + confidence + class)
Object Tracker
    |  compares against previous frame detections
    |  assigns persistent IDs to tracked objects
    v  (NEW egg events only -- not already counted)
Event Processor
    |
    +---> SQLite INSERT (egg_events table)
    |
    +---> WebSocket broadcast to all connected clients
              |
              v
         Browser Dashboard updates count in real-time
```

**Historical data flow (cold path):**

```
Browser Dashboard
    |
    v  (HTTP GET /api/eggs/today, /api/eggs/history)
FastAPI REST endpoint
    |
    v  (SQL query)
SQLite Database
    |
    v  (JSON response)
Browser Dashboard renders charts
```

**System startup flow:**

```
systemd service starts
    |
    v
Python main process launches
    |
    +---> Initialize Camera (OpenCV)
    +---> Load YOLO model (NCNN format)
    +---> Initialize SQLite database (create tables if needed)
    +---> Start FastAPI/Uvicorn web server (background thread or async)
    +---> Start detection loop (main async loop)
    |
    v
cloudflared tunnel (separate systemd service) exposes port to internet
```

## Component Detail

### 1. Camera Capture Module

**Responsibility:** Acquire frames at a controlled rate.

Do NOT capture at full camera FPS (30fps). Egg detection does not need real-time video -- eggs appear and sit in a nest box. Capture at 2-5 FPS to reduce CPU load and leave headroom for inference.

```python
# Pattern: frame grabber with controlled rate
class FrameGrabber:
    def __init__(self, camera_index: int = 0, target_fps: float = 3.0):
        self.cap = cv2.VideoCapture(camera_index)
        self.interval = 1.0 / target_fps

    async def frames(self):
        """Async generator yielding frames at target FPS."""
        while True:
            ret, frame = self.cap.read()
            if ret:
                yield frame
            await asyncio.sleep(self.interval)
```

**Key decisions:**
- Use V4L2 backend on Pi (not DirectShow -- that is Windows-only, existing code will need updating)
- Set camera resolution to 640x480 or 720p max -- higher is wasted since YOLO input is 640x640
- Handle camera disconnection gracefully (reconnect loop)

### 2. Detection Pipeline

**Responsibility:** Run YOLO model, return bounding boxes with class and confidence.

**Model format:** Export the trained YOLO model to NCNN format. NCNN is the best-performing inference runtime on Raspberry Pi 5 (ARM CPU, no GPU). It consistently outperforms ONNX Runtime and TFLite on Pi hardware by 2-3x.

```python
# Pattern: YOLO inference wrapper
from ultralytics import YOLO

class EggDetector:
    def __init__(self, model_path: str = "egg_model_ncnn_model"):
        self.model = YOLO(model_path, task="detect")

    def detect(self, frame: np.ndarray) -> list:
        results = self.model.predict(
            source=frame,
            conf=0.5,        # confidence threshold
            iou=0.45,        # NMS IoU threshold
            imgsz=640,
            verbose=False,
        )
        return results[0]  # single frame, single result
```

**Expected performance on Pi 5 (NCNN, 640x640 input):**
- YOLOv8n / YOLO11n: ~80-120ms per frame (~8-12 FPS)
- YOLOv8s / YOLO11s: ~200-300ms per frame (~3-5 FPS)
- Use the nano variant. For egg counting, accuracy difference between nano and small is minimal.

**Size classification approach:**
- Option A (recommended): Train a single YOLO model with 4 classes (small, medium, large, jumbo). The model learns size from visual context (egg relative to nest box, other eggs).
- Option B: Detect "egg" as one class, then classify size by bounding box area relative to a calibration reference. Simpler training data requirements but less accurate.
- The existing `object_measurer.py` uses A4 calibration for physical measurements. This approach works on a flat surface but is fragile in a nest box environment. Recommend Option A for production.

### 3. Object Tracker

**Responsibility:** Prevent double-counting. An egg sitting in a nest box will appear in hundreds of consecutive frames. The tracker assigns a persistent ID so each physical egg is counted exactly once.

**Recommended approach:** Ultralytics built-in tracker (BoT-SORT or ByteTrack). It works out of the box with the YOLO predict call:

```python
# Pattern: tracking mode
results = model.track(
    source=frame,
    persist=True,     # maintain track IDs across frames
    tracker="bytetrack.yaml",
    conf=0.5,
    verbose=False,
)
# Each detection now has a track ID
for box in results[0].boxes:
    track_id = box.id      # persistent across frames
    cls = box.cls           # egg size class
    conf = box.conf         # confidence
```

**Counting logic:**

```
Track ID first seen -> "NEW egg detected"
Track ID seen again -> skip (already counted)
Track ID disappears for N frames -> egg removed (optional: log removal)
```

Maintain a `seen_track_ids: set` that persists across frames. When a new track ID appears that is not in the set, fire a "new egg" event.

### 4. Event Processor

**Responsibility:** Bridge between detection pipeline and persistence/broadcast layers.

```python
# Pattern: event processing
class EventProcessor:
    def __init__(self, db: Database, ws_manager: WebSocketManager):
        self.db = db
        self.ws_manager = ws_manager
        self.seen_ids: set = set()

    async def process_detections(self, results):
        for box in results.boxes:
            track_id = int(box.id)
            if track_id not in self.seen_ids:
                self.seen_ids.add(track_id)

                egg_event = {
                    "track_id": track_id,
                    "size_class": CLASS_NAMES[int(box.cls)],
                    "confidence": float(box.conf),
                    "timestamp": datetime.utcnow().isoformat(),
                }

                await self.db.insert_egg_event(egg_event)
                await self.ws_manager.broadcast(egg_event)
```

### 5. SQLite Database

**Responsibility:** Persist egg counts and enable historical queries.

SQLite is the correct choice here. It runs in-process (no separate database server), handles the write volume trivially (under 100 writes/day), and survives Pi reboots. No need for PostgreSQL or any client-server database.

**Schema:**

```sql
CREATE TABLE IF NOT EXISTS egg_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    track_id INTEGER NOT NULL,
    size_class TEXT NOT NULL CHECK(size_class IN ('small','medium','large','jumbo')),
    confidence REAL NOT NULL,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS daily_summaries (
    date TEXT PRIMARY KEY,           -- YYYY-MM-DD
    total_count INTEGER DEFAULT 0,
    small_count INTEGER DEFAULT 0,
    medium_count INTEGER DEFAULT 0,
    large_count INTEGER DEFAULT 0,
    jumbo_count INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_egg_events_date ON egg_events(DATE(detected_at));
```

**Access pattern:** Use aiosqlite for async access from FastAPI. Alternatively, since write volume is trivial, synchronous sqlite3 in a background thread is fine.

### 6. Web Server (FastAPI + Uvicorn)

**Responsibility:** Serve the dashboard, provide REST API for historical data, manage WebSocket connections for real-time updates.

**Why FastAPI:** It supports both REST and WebSocket natively, has async support (important for not blocking the detection loop), and is the standard choice for Python APIs. Flask could work but its WebSocket support (via flask-socketio) adds complexity. FastAPI's native WebSocket support is cleaner.

```python
# Pattern: FastAPI with WebSocket
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles

app = FastAPI()
app.mount("/static", StaticFiles(directory="dashboard"), name="static")

class WebSocketManager:
    def __init__(self):
        self.connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)

    async def broadcast(self, data: dict):
        for ws in self.connections:
            try:
                await ws.send_json(data)
            except:
                self.connections.remove(ws)

ws_manager = WebSocketManager()

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws_manager.connect(ws)
    try:
        while True:
            await ws.receive_text()  # keep alive
    except WebSocketDisconnect:
        ws_manager.connections.remove(ws)

@app.get("/api/eggs/today")
async def get_today():
    # query SQLite for today's counts
    ...

@app.get("/api/eggs/history")
async def get_history(days: int = 30):
    # query SQLite for historical data
    ...
```

**API endpoints:**

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/eggs/today` | Current day egg counts by size |
| GET | `/api/eggs/history?days=30` | Daily totals for charting |
| GET | `/api/eggs/events?date=YYYY-MM-DD` | Individual egg events for a date |
| GET | `/api/status` | System health (camera ok, model loaded, uptime) |
| WS | `/ws` | Real-time egg detection events |

### 7. Dashboard UI

**Responsibility:** Display data, receive live updates.

Serve as static HTML/CSS/JS from the Pi. No build step needed. Use a lightweight approach:

- **Charts:** Chart.js (single CDN include, well-documented, handles bar/line charts for egg trends)
- **Reactivity:** Alpine.js or vanilla JS with WebSocket event handlers
- **Layout:** Simple responsive CSS (mobile-first since primary viewing is on phone)

```
dashboard/
  index.html          -- single-page dashboard
  css/
    style.css         -- responsive layout
  js/
    app.js            -- WebSocket connection, API calls, UI updates
    charts.js         -- Chart.js configuration for trends
```

No React, no Vue, no build pipeline. This is a single-page display that shows numbers and charts. Vanilla JS with a charting library is the right complexity level.

### 8. Remote Access (Cloudflare Tunnel)

**Responsibility:** Expose the Pi's local web server to the internet so the dashboard is accessible from a phone anywhere.

**Why Cloudflare Tunnel over alternatives:**
- **vs. port forwarding:** No static IP needed, no router configuration, no exposure of home network
- **vs. ngrok:** Free tier is permanent (ngrok free URLs rotate), no bandwidth limits that matter at this scale
- **vs. Tailscale:** Tailscale requires app installation on the phone. Cloudflare Tunnel exposes a normal HTTPS URL that works in any browser.

```bash
# One-time setup on Pi
cloudflared tunnel create egg-counter
cloudflared tunnel route dns egg-counter eggs.yourdomain.com
# Runs as systemd service
cloudflared tunnel run egg-counter
```

This gives a permanent HTTPS URL (e.g., `eggs.yourdomain.com`) that proxies to localhost:8000 on the Pi. WebSocket works through it natively.

**Requires:** A domain name (can be cheap, ~$10/year). Cloudflare must be the DNS provider for that domain.

**Alternative if no domain:** Tailscale with Funnel (exposes HTTPS endpoint via Tailscale's domain). Slightly easier setup, no domain needed, but the URL is less friendly.

## Patterns to Follow

### Pattern 1: Async Detection Loop with Web Server

Run the detection pipeline and web server in the same async event loop. The detection loop yields to the event loop between frames, allowing the web server to handle requests.

**What:** Single-process async architecture using asyncio.
**When:** Always -- this is the core pattern for the entire application.
**Example:**

```python
import asyncio
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start detection loop as background task
    task = asyncio.create_task(detection_loop())
    yield
    task.cancel()

app = FastAPI(lifespan=lifespan)

async def detection_loop():
    camera = FrameGrabber(camera_index=0, target_fps=3)
    detector = EggDetector("egg_model_ncnn_model")
    processor = EventProcessor(db, ws_manager)

    async for frame in camera.frames():
        results = detector.detect(frame)
        await processor.process_detections(results)
```

### Pattern 2: Debounced Event Emission

Eggs do not appear and disappear rapidly. Once an egg is detected, suppress re-emission of events for that track ID. Use a cooldown mechanism so brief tracking glitches (ID lost and re-assigned) do not cause double counts.

**What:** Time-based debouncing on top of track ID deduplication.
**When:** Event processing -- when the tracker loses and re-acquires an egg.
**Example:**

```python
class EventProcessor:
    def __init__(self):
        self.seen_ids: dict[int, float] = {}  # track_id -> last_seen_timestamp
        self.cooldown_seconds = 300  # 5 minutes

    def is_new_egg(self, track_id: int) -> bool:
        now = time.time()
        if track_id in self.seen_ids:
            return False
        # Also check if a very similar position was recently counted
        # (handles tracker ID reassignment)
        self.seen_ids[track_id] = now
        return True

    def cleanup_old_ids(self):
        """Remove track IDs older than cooldown to free memory."""
        cutoff = time.time() - self.cooldown_seconds
        self.seen_ids = {
            tid: ts for tid, ts in self.seen_ids.items()
            if ts > cutoff
        }
```

### Pattern 3: Graceful Degradation

Camera may disconnect. Model may fail on corrupted frame. Network may drop. Each failure mode should degrade gracefully without crashing the whole system.

**What:** Component-level error isolation with health reporting.
**When:** All runtime operations.
**Example:**

```python
async def detection_loop():
    while True:
        try:
            frame = camera.grab()
            if frame is None:
                logger.warning("Camera returned no frame, retrying...")
                await camera.reconnect()
                continue

            results = detector.detect(frame)
            await processor.process_detections(results)

        except Exception as e:
            logger.error(f"Detection loop error: {e}")
            await asyncio.sleep(5)  # back off before retry
```

### Pattern 4: Daily Rollover

At midnight, aggregate the day's egg events into a summary row and optionally reset the "today" display. This keeps the events table manageable and provides fast access to historical data.

**What:** Scheduled aggregation task.
**When:** Daily at midnight (or on first request of a new day).
**Example:**

```python
async def daily_rollover():
    """Run daily at midnight to create summary."""
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    counts = await db.get_counts_for_date(yesterday)
    await db.upsert_daily_summary(yesterday, counts)
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Running Inference at Full Camera FPS

**What:** Capturing and processing every frame the camera produces (30 FPS).
**Why bad:** YOLO inference on Pi 5 takes 80-120ms per frame (nano model, NCNN). At 30 FPS you need 33ms per frame -- physically impossible. Frames queue up, memory grows, latency increases, Pi overheats.
**Instead:** Capture at 2-5 FPS. Eggs do not move. Use `asyncio.sleep()` between captures.

### Anti-Pattern 2: Polling from the Dashboard

**What:** Dashboard uses `setInterval(() => fetch('/api/eggs'), 1000)` to poll for new eggs.
**Why bad:** Wastes bandwidth on a potentially metered connection (remote access), adds latency (up to 1 second delay), and creates unnecessary load on the Pi.
**Instead:** WebSocket push. The Pi broadcasts the instant an egg is detected.

### Anti-Pattern 3: Storing Frames or Images in the Database

**What:** Saving the camera frame or annotated image for every detection.
**Why bad:** SD card on the Pi has limited space and limited write endurance. At 3 FPS, even storing only detection frames fills storage quickly.
**Instead:** Store only structured data (timestamp, size class, confidence). If images are desired for debugging, save them to a rolling buffer on disk (keep last N, delete oldest).

### Anti-Pattern 4: Using Flask + flask-socketio for WebSocket

**What:** Adding Socket.IO on top of Flask for real-time communication.
**Why bad:** Socket.IO adds a protocol layer on top of WebSocket, requires a matching client library, and is overkill for a simple broadcast pattern. Flask's WSGI model also does not handle async well.
**Instead:** FastAPI native WebSocket support. Standard WebSocket protocol. Browser's built-in `WebSocket` API on the client. No extra libraries.

### Anti-Pattern 5: Running a Separate Database Server

**What:** Installing PostgreSQL or MySQL on the Pi.
**Why bad:** Unnecessary resource consumption, operational complexity, and memory overhead for a system that processes <100 writes/day from a single client.
**Instead:** SQLite. In-process, zero configuration, file-based, built into Python stdlib.

### Anti-Pattern 6: Complex Frontend Build Pipeline

**What:** Using React/Next.js/Vite with npm build for the dashboard.
**Why bad:** Adds build tooling dependencies on the Pi, complicates deployment, and is unnecessary for a single-page dashboard that displays numbers and charts.
**Instead:** Static HTML/CSS/JS with Chart.js from CDN. Deploy by copying files.

## Scalability Considerations

| Concern | At 1 user (current) | At 5 users | At 100+ eggs/day |
|---------|---------------------|------------|-------------------|
| **WebSocket connections** | Trivial | Still trivial | N/A (same connections) |
| **Database writes** | <100/day, no issue | Same writes, more reads | Consider daily_summaries for fast reads |
| **Inference load** | 3 FPS is fine | Same -- inference is independent of viewers | May need faster model or lower FPS |
| **Network bandwidth** | Minimal (JSON only) | Still minimal | N/A |
| **Storage** | <1MB/year of data | Same | Same -- only structured data |

This system does not need to scale beyond its current design. The Pi 5 is the ceiling. If more performance were needed (multiple cameras, higher throughput), the answer is a more powerful edge device, not architectural changes.

## Build Order (Dependency Chain)

Components should be built in this order because each layer depends on the one before it:

```
Phase 1: Detection Pipeline (standalone, testable without web)
  1a. Camera capture module (OpenCV, V4L2)
  1b. YOLO model training + NCNN export
  1c. Object tracker integration
  1d. Counting logic with deduplication
  --> Deliverable: CLI tool that prints "New egg: large (0.92 conf)" to stdout

Phase 2: Data Persistence
  2a. SQLite schema + database module
  2b. Event processor (connects detection to database)
  2c. Daily aggregation
  --> Deliverable: Eggs are counted and stored in SQLite

Phase 3: Web Dashboard
  3a. FastAPI server with REST API endpoints
  3b. WebSocket broadcast integration
  3c. Dashboard HTML/JS/CSS
  3d. Chart.js historical trends
  --> Deliverable: Working dashboard on local network

Phase 4: Remote Access + Hardening
  4a. Cloudflare Tunnel setup
  4b. systemd service files (auto-start on boot)
  4c. Logging and health monitoring
  4d. Graceful error recovery
  --> Deliverable: Production-ready system accessible from phone
```

**Why this order:**
- Phase 1 has zero dependencies and validates the hardest technical risk (can YOLO detect and count eggs accurately on Pi 5?)
- Phase 2 is a thin persistence layer that wraps Phase 1 output
- Phase 3 consumes Phase 2 data -- it cannot show anything without detection + storage working
- Phase 4 is operational polish that wraps the working system for reliability

## Directory Structure

```
egg-counter/
  src/
    detection/
      __init__.py
      camera.py          # FrameGrabber - camera capture
      detector.py         # EggDetector - YOLO inference wrapper
      tracker.py          # Tracking + deduplication logic
      processor.py        # EventProcessor - bridge to storage/broadcast
    web/
      __init__.py
      server.py           # FastAPI app, routes, WebSocket
      models.py           # Pydantic models for API responses
    db/
      __init__.py
      database.py         # SQLite operations, schema migration
      queries.py          # SQL query functions
    config.py             # Configuration (camera index, model path, etc.)
    main.py               # Application entry point
  dashboard/
    index.html
    css/
      style.css
    js/
      app.js
      charts.js
  models/
    README.md             # Instructions for model training/export
    # trained model files go here (not in git)
  scripts/
    train_model.py        # YOLO training script
    export_model.py       # Export to NCNN
    setup_tunnel.sh       # Cloudflare Tunnel setup
    install_service.sh    # systemd service installation
  systemd/
    egg-counter.service   # systemd unit file
    cloudflared.service   # tunnel service (if not using cloudflared's own)
  tests/
    test_tracker.py
    test_database.py
    test_api.py
  requirements.txt
  pyproject.toml
```

## Sources

- Training data knowledge of Ultralytics YOLO documentation (deployment guides, Raspberry Pi guides, tracking documentation)
- Training data knowledge of FastAPI WebSocket support
- Training data knowledge of Cloudflare Tunnel documentation
- Training data knowledge of NCNN framework performance on ARM
- Existing project code analysis (camera_scanner.py, object_measurer.py, capture_images.py)

**Confidence note:** All architecture recommendations are based on training data (cutoff early 2025). The YOLO ecosystem, FastAPI, and Cloudflare Tunnel are all stable, well-established technologies unlikely to have changed architecturally. However, specific version numbers and exact inference benchmarks should be verified against current Ultralytics documentation before implementation. Overall confidence: MEDIUM-HIGH.
