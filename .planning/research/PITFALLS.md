# Domain Pitfalls

**Domain:** Raspberry Pi edge CV egg counting and classification with real-time web dashboard
**Researched:** 2026-03-19
**Confidence:** MEDIUM (training data only -- web search and doc fetch unavailable during research; verify Ultralytics Raspberry Pi docs and NCNN benchmarks against current versions)

---

## Critical Pitfalls

Mistakes that cause rewrites, broken inference, or unusable systems.

---

### Pitfall 1: Running Full-Size YOLO Without Export Optimization

**What goes wrong:** Developers load a PyTorch `.pt` YOLO model directly on the Pi and get 0.5-2 FPS. They assume "YOLO is fast" based on desktop/GPU benchmarks, then spend weeks trying to optimize Python code when the real bottleneck is the model format.

**Why it happens:** Ultralytics tutorials default to PyTorch inference. Desktop benchmarks show 60+ FPS with a GPU. Nobody warns you that the same model in `.pt` format on a Pi 5 ARM CPU runs 10-50x slower than an exported optimized format.

**Consequences:**
- System is unusable for real-time counting (misses eggs laid between slow frames)
- Developers blame the Pi hardware and consider expensive upgrades
- Wasted effort optimizing application code when the model format is the bottleneck

**Prevention:**
- Export the model to **NCNN format** before deploying to Pi. NCNN is purpose-built for ARM inference and consistently benchmarks fastest on Raspberry Pi (typically 3-8x faster than PyTorch on Pi 5).
- Use YOLOv8n or YOLO11n (nano) variants. The "n" model is the correct starting point for Pi. Do NOT start with "s" or "m" hoping to "optimize later."
- Benchmark on the actual Pi hardware early -- in the first sprint, not after building the whole pipeline.
- Target: YOLOv8n-NCNN on Pi 5 should achieve roughly 15-30 FPS at 640x640 input. If you are seeing less than 5 FPS, something is wrong with the export or input pipeline.

**Detection (warning signs):**
- Inference time per frame exceeds 200ms (should be 30-70ms with NCNN nano)
- CPU usage pegged at 100% on a single core during inference
- You are importing `torch` on the Pi (you should not need PyTorch installed for NCNN inference)

**Phase:** Must be addressed in Phase 1 (model training and export). Wrong format here cascades into every later phase.

---

### Pitfall 2: Double-Counting Eggs That Stay in Frame

**What goes wrong:** The system detects eggs every frame. Since eggs sit in the nest box (they do not leave the frame), every inference cycle "finds" the same eggs again. The count inflates rapidly -- 6 real eggs become 600 in minutes.

**Why it happens:** YOLO is a per-frame detector. It has no concept of object identity across frames. Most YOLO tutorials show detection but not tracking or deduplication. This is the single most common failure mode in counting-based CV projects.

**Consequences:**
- Egg counts are wildly inflated and completely useless
- Users lose trust in the system immediately
- Fixing this after building the full pipeline requires rearchitecting the counting logic

**Prevention:**
- Implement **stateful count tracking** from day one. Two viable approaches:
  1. **Object tracking** (e.g., ByteTrack, BoTSORT via Ultralytics' built-in tracker): Assign persistent IDs to detected objects across frames. Only increment count when a new ID appears. This is the recommended approach.
  2. **Delta-based counting**: Compare current frame detections against a "known eggs" state. Only count genuinely new detections (new bounding box that does not overlap significantly with existing tracked positions).
- The Ultralytics library includes built-in tracking (`model.track()` instead of `model.predict()`). Use it.
- Define a **minimum persistence threshold**: an object must be detected in N consecutive frames (e.g., 3-5) before being counted as a real egg. This also filters false positives.

**Detection (warning signs):**
- Egg count increases even when no new eggs are laid
- Count rises linearly with time rather than in discrete steps
- Count resets on system restart (because "known eggs" state was lost)

**Phase:** Must be addressed in Phase 1/2 (core detection pipeline). This is architectural -- cannot be patched in later without rewriting the counting logic.

---

### Pitfall 3: Training on Clean Studio Images, Deploying in a Dirty Nest Box

**What goes wrong:** The YOLO model is trained on a dataset of eggs photographed on clean backgrounds with even lighting. In the real nest box, eggs sit on straw/shavings, are partially occluded by hay or other eggs, lighting changes throughout the day, and the camera catches dust/condensation. Detection accuracy drops from 95%+ (validation) to 40-60% (production).

**Why it happens:** Most publicly available egg datasets (e.g., from Roboflow) are photographed in controlled conditions. The domain gap between training data and deployment environment is enormous but invisible during training/validation.

**Consequences:**
- Missed detections (eggs not counted)
- False positives (straw clumps or shadows detected as eggs)
- Size classification completely unreliable due to perspective/lighting variation
- Model appears to work in testing but fails in production

**Prevention:**
- **Collect training data from YOUR actual nest box** with YOUR camera in YOUR lighting conditions. Even 100-200 annotated images from the real environment vastly outperform 2,000 stock images.
- Use a **staged approach**: start with a pretrained egg model (transfer learning from public dataset), deploy it, then actively collect failure cases from the real environment to retrain.
- Augment training data aggressively: vary brightness (+/- 40%), add noise, random crops, simulate partial occlusion.
- Include negative examples: empty nest, straw-only, shadows, dirty lens.
- Test at multiple times of day -- morning, noon, and evening lighting differ drastically in a nest box.

**Detection (warning signs):**
- Validation mAP is 90%+ but real-world detection feels unreliable
- Model fires on shadows or straw consistently
- Detection accuracy varies dramatically by time of day
- Eggs partially buried in bedding are never detected

**Phase:** Phase 1 (model training) initial setup, but requires a Phase 2 iteration loop (deploy, collect failures, retrain). Budget for at least 2-3 retraining cycles.

---

### Pitfall 4: Memory Exhaustion and SD Card Death on the Pi

**What goes wrong:** The Pi runs out of RAM during inference (especially if OpenCV, YOLO, and a web server all run simultaneously), or the SD card wears out from constant writes (logging, frame saves, database writes). System crashes or becomes unresponsive within days/weeks.

**Why it happens:** Pi 5 has 4GB or 8GB RAM. Loading NCNN model + OpenCV + Python runtime + web server can consume 1.5-3GB. If frames are buffered in memory or logging is verbose, the system swaps to SD card, which accelerates wear. SD cards have limited write cycles and are not designed for continuous I/O.

**Consequences:**
- System crashes during inference (OOM killer terminates the process)
- SD card corruption loses all historical data
- Repeated crashes degrade SD card life further
- System appears to "randomly" fail -- hard to debug

**Prevention:**
- **Memory**: Monitor RSS of the main process. Set hard limits. Process frames in-place (do not accumulate frame buffers). Use `imgsz=640` or even `imgsz=320` -- the small nest box scene does not need high resolution. Release frames immediately after inference.
- **SD card**: Use an **external USB SSD** for the database and any persistent writes. Keep the SD card read-only after boot where possible. Minimize logging verbosity. Never save raw frames to disk in production -- only save on detection events, and cap storage.
- **Swap**: Configure a small swap file (512MB) on the USB SSD, not the SD card.
- Use `systemd` with automatic restart on crash, but also add a watchdog that alerts on repeated restarts (do not silently restart forever).
- Test with `stress-ng` or similar while inference runs to confirm stability under load.

**Detection (warning signs):**
- `dmesg` shows OOM killer messages
- System becomes sluggish after hours of uptime
- SD card shows read-only filesystem errors
- Database corruption on unexpected power loss

**Phase:** Phase 2 (deployment pipeline). Must be designed into the infrastructure, not bolted on.

---

### Pitfall 5: WebSocket Connection Treated as Always-On

**What goes wrong:** The dashboard opens a WebSocket to the Pi and assumes it stays connected. In reality: the phone goes to sleep, the browser tab backgrounding throttles/kills the socket, network interruptions occur (especially on cellular), and the Pi itself may restart. The dashboard shows stale data or a permanent "loading" spinner with no indication that the connection is dead.

**Why it happens:** WebSocket examples show the "happy path" -- open connection, send messages, done. Nobody tests what happens when the phone locks, the user switches apps, or the Pi reboots at 3am. Mobile browsers aggressively kill background WebSocket connections.

**Consequences:**
- User sees outdated egg counts, does not realize data is stale
- Dashboard appears broken after phone wakes from sleep
- No reconnection = user must manually refresh (defeats the "live" purpose)
- If the Pi restarts, all connected clients are silently disconnected

**Prevention:**
- Implement **automatic reconnection with exponential backoff** on the client side. When the socket closes or errors, retry at 1s, 2s, 4s, 8s... capped at 30s.
- Add a **heartbeat/ping-pong mechanism**: client sends ping every 15-30 seconds. If no pong within 5 seconds, assume disconnected and trigger reconnection.
- Show a **visible connection status indicator** on the dashboard (green dot = connected, red dot = reconnecting). Never let stale data appear to be current.
- On reconnection, **fetch current state via REST** before relying on WebSocket incremental updates. The client missed events while disconnected.
- Use the `visibilitychange` browser event to detect tab backgrounding and trigger a reconnect + state sync when the tab becomes visible again.

**Detection (warning signs):**
- Dashboard shows yesterday's count after being left open overnight
- No error shown when the Pi goes offline
- Users report "it stops updating sometimes"
- Dashboard works on desktop but is unreliable on mobile

**Phase:** Phase 3 (dashboard/frontend). Must be part of the initial WebSocket implementation, not a polish item.

---

## Moderate Pitfalls

---

### Pitfall 6: Ignoring Camera Warm-Up and Auto-Exposure Lag

**What goes wrong:** The USB camera's first 5-30 frames after startup are dark, green-tinted, or wildly overexposed while auto-exposure/auto-white-balance settle. The model fires false positives or misses eggs on these frames. If the system restarts frequently, this happens repeatedly.

**Prevention:**
- Discard the first 30 frames (or ~2 seconds of capture) after camera initialization before running inference.
- If possible, lock exposure and white balance settings manually after the camera stabilizes, rather than relying on continuous auto-adjustment that can fluctuate with lighting changes.
- Test with the camera pointed at the actual nest box at different times of day to find stable settings.

**Detection (warning signs):**
- Burst of false positives immediately after system start
- Detection accuracy is inconsistent for the first minute of operation
- Log shows detections with very low confidence in the first few seconds

**Phase:** Phase 1 (camera capture pipeline).

---

### Pitfall 7: Size Classification Without Reference Calibration

**What goes wrong:** The model is asked to classify eggs as small/medium/large/jumbo based purely on pixel dimensions in the frame. But pixel size depends on distance from camera, camera angle, lens distortion, and where in the frame the egg appears. An egg near the camera looks "jumbo" while the same egg further away looks "small."

**Prevention:**
- Use **relative sizing** rather than absolute pixel dimensions. If multiple eggs are visible, compare ratios.
- **Calibrate with a known reference**: place a reference object of known size in the camera's field of view (even temporarily during setup) to establish a pixels-per-cm ratio at a fixed distance.
- Accept that visual size classification will have lower accuracy than weight-based classification. Target 3 categories (small, medium, large) rather than 4 -- the distinction between large and jumbo is very hard to make visually.
- Train the classifier on images from the **exact camera position and angle** that will be used in production. If the camera moves, recalibrate.

**Detection (warning signs):**
- The same egg is classified as different sizes depending on its position in frame
- Size distribution is heavily skewed (e.g., everything classified as "large")
- Moving the camera even slightly changes all classifications

**Phase:** Phase 1 (model training), with validation in Phase 2 (deployment).

---

### Pitfall 8: Running Inference on Every Frame

**What goes wrong:** The system captures frames at 30 FPS and runs YOLO inference on every single one. This maxes out the CPU, generates excessive heat (throttling), and is completely unnecessary -- eggs do not move. The Pi becomes unresponsive for the web server.

**Prevention:**
- **Inference at 1-2 FPS is sufficient** for stationary egg counting. Eggs appear over minutes, not milliseconds.
- Run inference on every Nth frame (e.g., every 15th-30th frame from a 30 FPS capture).
- Alternatively, use **motion detection** (simple frame differencing with OpenCV) as a gate: only run YOLO when the scene changes. Hens entering/leaving trigger inference; static scenes skip it.
- This frees ~95% of CPU time for the web server, database writes, and system stability.

**Detection (warning signs):**
- CPU temperature exceeds 80C consistently
- CPU throttling messages in `dmesg` or `vcgencmd get_throttled`
- Web dashboard responds slowly or times out
- Pi 5 fan runs at maximum constantly

**Phase:** Phase 1 (inference pipeline design). Architectural decision that must be made early.

---

### Pitfall 9: No Persistence Across Pi Reboots

**What goes wrong:** The daily egg count and detection state are kept in memory only. When the Pi reboots (power outage, system update, crash), the count resets to zero. Historical data is lost. "Known eggs" tracking state is lost, causing re-counting of eggs already in the nest.

**Prevention:**
- Persist the count and detection state to a **SQLite database** on an external USB SSD (not the SD card).
- Write detection events (timestamp, count, sizes) to the database immediately on each new detection. Do not batch in memory.
- On startup, load the current day's count from the database. Compare against what the camera currently sees to reconcile state.
- Implement a **startup reconciliation routine**: on boot, run inference on the current scene, compare against the last known state from the database, and adjust the count accordingly (do not just add to zero).

**Detection (warning signs):**
- Count resets after any restart
- Historical data disappears after power outage
- System shows different counts after a reboot than before

**Phase:** Phase 2 (data persistence layer). Must exist before the dashboard is built.

---

### Pitfall 10: Exposing the Pi Directly to the Internet for Remote Access

**What goes wrong:** To enable remote dashboard access, developers port-forward the Pi's web server directly to the public internet, or use a simple dynamic DNS setup without authentication. The Pi gets scanned, attacked, and potentially compromised within hours.

**Prevention:**
- **Never expose the Pi directly.** Use one of these approaches:
  1. **Cloudflare Tunnel (recommended for this project)**: Free, zero-config, encrypted tunnel from Pi to Cloudflare edge. Dashboard gets a public URL without any port forwarding. Handles HTTPS automatically.
  2. **Tailscale/WireGuard VPN**: Creates a private network. Dashboard is only accessible to authenticated devices on the VPN.
- If using Cloudflare Tunnel, add Cloudflare Access (free tier) for basic authentication (email OTP or similar).
- Do NOT run the Pi web server as root.
- Keep the Pi's OS and packages updated -- unattended-upgrades for security patches.

**Detection (warning signs):**
- Pi has port 80/443/8080 forwarded in router settings
- `nmap` scan from outside the network shows open ports
- Unexpected SSH login attempts in auth.log
- Pi performance degrades from bot scanning/attacks

**Phase:** Phase 3 (remote access). Must be designed before the dashboard goes live.

---

## Minor Pitfalls

---

### Pitfall 11: Not Handling Power Loss Gracefully

**What goes wrong:** Farm environments have unreliable power. A sudden power cut mid-database-write corrupts SQLite. The SD card filesystem gets damaged. On reboot, the system fails to start.

**Prevention:**
- Use SQLite with **WAL (Write-Ahead Logging) mode** -- it is far more resilient to crash recovery than the default journal mode.
- Mount the root filesystem as read-only where feasible. Use `overlayfs` or Raspberry Pi OS's built-in overlay filesystem option.
- Consider a small UPS (Uninterruptible Power Supply) HAT for the Pi (~$20-30) that provides 30-60 seconds of battery to allow clean shutdown on power loss.
- Add a `systemd` shutdown script that cleanly closes the database and camera on SIGTERM.

**Phase:** Phase 2 (deployment hardening).

---

### Pitfall 12: Ignoring Thermal Throttling in Enclosed Spaces

**What goes wrong:** The Pi is placed in a weatherproof enclosure near the nest box. Without airflow, the CPU throttles under sustained inference load, dropping FPS and causing detection gaps. In summer, the enclosure temperature can exceed the Pi's operating range.

**Prevention:**
- Use the Pi 5's **active cooler** (official fan + heatsink). It is inexpensive and essential for sustained workloads.
- Ensure the enclosure has ventilation holes or use a vented case.
- Monitor CPU temperature via `vcgencmd measure_temp` and log it. Alert if it exceeds 75C.
- The inference-on-change strategy (Pitfall 8) dramatically reduces thermal load.

**Phase:** Phase 2 (hardware deployment).

---

### Pitfall 13: Timezone and Day Boundary Confusion in Counts

**What goes wrong:** The Pi's system clock is set to UTC. "Today's eggs" resets at midnight UTC instead of midnight local time. The dashboard shows confusing counts around the day boundary. Historical charts have days shifted by several hours.

**Prevention:**
- Set the Pi's timezone to the farm's local timezone and verify with `timedatectl`.
- Store timestamps in UTC in the database but always convert to local time for display and for day-boundary calculations.
- Define "egg day" explicitly in configuration (e.g., day resets at 4:00 AM local time, since hens do not lay at 4 AM).
- Test the day boundary logic around DST transitions.

**Phase:** Phase 2 (data layer) and Phase 3 (dashboard display).

---

### Pitfall 14: Overcomplicating the Dashboard Tech Stack

**What goes wrong:** Developers reach for React + Next.js + TypeScript + Tailwind + state management library + component library for a dashboard that shows one number, a size breakdown, and a chart. The build toolchain alone introduces more complexity and failure modes than the entire CV pipeline.

**Prevention:**
- This is a **single-page, single-user dashboard.** Use the simplest approach that works:
  - A lightweight framework (e.g., vanilla JS with a charting library, or a minimal framework like Alpine.js/htmx)
  - Alternatively, if you are comfortable with React, use a single-page Vite + React setup. Do NOT add Next.js -- there is no SSR need for a dashboard displaying live data.
- The dashboard has ~3 views: today's count, size breakdown, historical chart. This does not justify a complex frontend architecture.
- Use a proven charting library (Chart.js is sufficient; do not reach for D3.js).

**Phase:** Phase 3 (dashboard). Choose stack before writing any frontend code.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Model training | Training on stock images, not real nest box images (Pitfall 3) | Collect 100+ images from actual deployment environment |
| Model export | Using PyTorch format instead of NCNN (Pitfall 1) | Export to NCNN before any Pi testing |
| Inference pipeline | Running inference on every frame (Pitfall 8) | Design 1-2 FPS or motion-gated inference from the start |
| Counting logic | Double-counting stationary eggs (Pitfall 2) | Use Ultralytics tracking or delta-based counting from day one |
| Size classification | No perspective/distance calibration (Pitfall 7) | Calibrate from fixed camera position, train on in-situ images |
| Data persistence | In-memory state lost on reboot (Pitfall 9) | SQLite on USB SSD with WAL mode from the start |
| Hardware deployment | Thermal throttling in enclosure (Pitfall 12) | Active cooler + ventilation + temperature monitoring |
| Hardware deployment | SD card death from writes (Pitfall 4) | USB SSD for all persistent I/O |
| WebSocket dashboard | Assuming always-connected (Pitfall 5) | Reconnection + heartbeat + state sync on reconnect |
| Remote access | Direct internet exposure (Pitfall 10) | Cloudflare Tunnel or Tailscale, never port forwarding |
| Dashboard tech | Overengineered frontend (Pitfall 14) | Simple stack: Vite + minimal framework + Chart.js |
| Day boundaries | UTC vs local time confusion (Pitfall 13) | Configure timezone, define "egg day" reset time |

---

## Sources and Confidence Notes

All findings in this document are based on training data knowledge of Raspberry Pi computer vision deployments, YOLO/Ultralytics edge deployment patterns, and common failure modes reported in Raspberry Pi + CV project communities through early 2025. Web search and official documentation fetching were unavailable during this research session.

**Items that should be verified against current documentation:**
- NCNN export performance benchmarks on Pi 5 (verify against current Ultralytics Raspberry Pi deployment guide)
- Ultralytics built-in tracking API (`model.track()`) -- confirm current syntax and supported trackers
- Cloudflare Tunnel free tier limitations and setup for Raspberry Pi
- Pi 5 thermal throttling thresholds and active cooler specifications
- YOLOv11/YOLO11 availability and naming conventions (Ultralytics renamed from YOLOv8 in late 2024; verify current naming)

**Confidence by pitfall category:**
| Category | Confidence | Reason |
|----------|------------|--------|
| Model format (Pitfall 1) | HIGH | Well-documented across many sources; fundamental Pi limitation |
| Double-counting (Pitfall 2) | HIGH | Universal failure in counting CV projects; very well-known |
| Domain gap (Pitfall 3) | HIGH | Standard ML deployment problem, extensively documented |
| Memory/SD card (Pitfall 4) | HIGH | Hardware limitation, extensively documented for Pi projects |
| WebSocket reliability (Pitfall 5) | HIGH | Universal web development issue, well-documented |
| Camera warm-up (Pitfall 6) | MEDIUM | Known issue but exact frame count varies by camera model |
| Size calibration (Pitfall 7) | MEDIUM | Specific to this project's visual estimation approach |
| Frame rate (Pitfall 8) | HIGH | Obvious but frequently ignored in tutorials |
| Persistence (Pitfall 9) | HIGH | Fundamental software engineering practice |
| Security (Pitfall 10) | HIGH | Critical and well-documented |
| Power loss (Pitfall 11) | MEDIUM | Farm-specific; severity depends on local power reliability |
| Thermal (Pitfall 12) | HIGH | Well-documented Pi limitation |
| Timezone (Pitfall 13) | MEDIUM | Easy to overlook but straightforward to fix |
| Dashboard complexity (Pitfall 14) | MEDIUM | Subjective; depends on developer preferences |
