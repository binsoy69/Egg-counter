# Feature Landscape

**Domain:** Real-time egg counting and size classification with web dashboard (hobby farm)
**Researched:** 2026-03-19
**Confidence:** MEDIUM -- based on domain knowledge of YOLO edge detection, Raspberry Pi ML, IoT dashboards, and poultry farm monitoring systems. Web search was unavailable; findings are grounded in the project's stated requirements, existing codebase analysis, and established patterns for this class of system.

---

## Table Stakes

Features users expect. Missing = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Egg detection (counting)** | The core product promise. If it cannot reliably detect and count eggs, nothing else matters. | High | YOLO model must be trained/fine-tuned on egg images in nest box context. Detection confidence threshold tuning is critical -- too low = false positives from bedding/debris, too high = missed eggs. |
| **Size classification (S/M/L/XL)** | Second core promise. Users want to know what they collected, not just how many. | High | Visual estimation from bounding box dimensions (no scale). Requires calibration reference or known camera distance. Accuracy will be lower than weight-based but acceptable for hobby use. Classification boundaries need defining (USDA standards or custom). |
| **Daily count display** | The most basic useful output: "How many eggs today?" Must be answered at a glance. | Low | Simple counter incremented on detection, reset at configurable time (e.g., midnight or dawn). Broken down by size category. |
| **Historical data (daily/weekly trends)** | Without history, the dashboard is just a counter -- no better than a whiteboard. Users want to see production trends over time. | Medium | Requires persistent storage (database). Simple line/bar charts showing eggs per day, per week. Size distribution over time. |
| **Real-time push updates (WebSocket)** | Stated requirement. Polling is unacceptable when user is watching remotely -- they want to see the count update the moment an egg appears. | Medium | WebSocket connection from Pi to dashboard. Must handle reconnection gracefully when network drops. |
| **Remote access from phone** | Explicitly required. Dashboard must be usable outside the local network. | Medium | Options: Cloudflare Tunnel, Tailscale, or hosted backend that Pi pushes to. Must work on mobile browsers without app install. |
| **Mobile-responsive dashboard** | If remote access is the primary use case (checking from phone throughout the day), the UI must be designed for small screens first. | Low | Mobile-first responsive layout. Large numbers, readable charts, touch-friendly. |
| **De-duplication (same egg not counted twice)** | Eggs sit in the nest box. Camera runs continuously. Without de-duplication, the same 3 eggs get counted as 300 over the day. This is the single most critical correctness feature. | High | Must track egg positions across frames. When a new egg appears in a position where there was not one before, count it. When eggs are removed (collected), reset that position. This is fundamentally a state management problem, not just detection. |
| **Configurable daily reset** | Egg counts need to reset for the new "day." Farm days often start at dawn, not midnight. | Low | Configurable reset time. Manual reset button on dashboard as backup. |
| **System health indicator** | User checks remotely. If the Pi is offline, camera disconnected, or model crashed, the dashboard must say so -- not just show stale data. | Low | Heartbeat/last-seen timestamp. "Pi last reported 2 minutes ago" vs "Pi offline since 3:00 PM." Dashboard shows stale data warning when heartbeat is missed. |

---

## Differentiators

Features that set product apart. Not expected, but valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Egg detection event log** | "An egg appeared at 10:32 AM (large)" -- gives a timeline of the day's laying activity. Useful for understanding hen behavior and identifying which hens lay when (if nest boxes are separated). | Low | Log each detection event with timestamp and classification. Display as scrollable list on dashboard. |
| **Collection tracking** | "I collected 6 eggs at 4 PM" -- user taps a button when they collect eggs. Dashboard then shows: produced today vs. collected vs. remaining in box. | Medium | Requires manual user input (button press on dashboard). Resets the "in box" counter. Useful for knowing if eggs are still waiting. |
| **Detection confidence display** | Show the model's confidence score for each detection. Helps user build trust in the system and identify when conditions are degrading accuracy. | Low | Already available from YOLO inference output. Display on dashboard as a quality metric. |
| **Lighting/image quality warnings** | "Camera image is too dark -- detections may be unreliable." Proactively warn when conditions degrade. | Medium | Analyze frame brightness/contrast before inference. Warn if below threshold. The existing codebase already has brightness analysis (camera_scanner.py checks mean brightness). |
| **Weekly/monthly production reports** | Summary emails or dashboard pages: "This week: 42 eggs (12 small, 18 medium, 10 large, 2 jumbo). Up 8% from last week." | Medium | Aggregation queries on historical data. Nice charts (bar chart by size, line chart trend). Comparisons to previous periods. |
| **Laying pattern analysis** | "Your hens lay most between 8-11 AM." Heat map of detection times. Identifies patterns over time. | Medium | Requires accumulating several weeks of data. Time-of-day histogram. Useful for knowing when to check boxes. |
| **Model retraining pipeline** | User captures images of missed/false detections, marks them, and these feed back into model improvement. | High | Needs annotation UI, training pipeline, model deployment workflow. Probably overkill for v1 but valuable long-term. The existing capture_images.py is an early step toward this. |
| **Multi-camera/multi-box support** | Monitor multiple nest boxes with separate cameras. Each box gets its own count. | High | Requires camera multiplexing, per-box state tracking, dashboard layout for multiple feeds. Pi 5 can likely handle 2-3 cameras with YOLO if using small model variant. |
| **Snapshot on detection** | Save a cropped image when a new egg is detected. Viewable in the event log. Useful for verifying detection accuracy without live feed. | Low | Save frame crop on detection event. Store with timestamp. Display in event log. Storage management needed (auto-delete after N days). |
| **Export data (CSV/JSON)** | Let user download their egg production data for spreadsheets, sharing with other farmers, or personal records. | Low | API endpoint or dashboard button that dumps historical data. |

---

## Anti-Features

Features to explicitly NOT build.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Live camera feed on dashboard** | Explicitly out of scope per PROJECT.md. Streaming video from Pi consumes significant bandwidth, adds latency concerns, and raises privacy considerations. The value is in the data, not watching hens sit. | Show detection events, counts, and optional snapshots on detection. |
| **Push notifications (v1)** | Deferred to v2 per PROJECT.md. Adds complexity (service workers, notification permissions, mobile OS integration) that delays core value delivery. | Dashboard-only alerts. Add push in v2 after core is proven. |
| **Multi-user accounts/auth** | Single user system. Adding user management adds significant complexity for zero value. | Single-user access. If security is needed, use basic auth or network-level access control (Tailscale). |
| **Egg weight measurement** | Requires additional hardware (scale). PROJECT.md explicitly scopes to visual estimation only. | Visual size classification from bounding box dimensions. Clearly label as "estimated" on dashboard. |
| **Complex ML model training UI** | Building a full annotation and training pipeline is a separate project. Massively increases scope. | Provide capture_images.py for collecting training data. Training happens offline on a workstation. |
| **Egg quality/defect detection** | Detecting cracks, dirt, or abnormalities is a substantially harder ML problem requiring different training data and likely higher resolution imaging. | Focus on counting and size. Quality is a different product. |
| **Integration with poultry management software** | No standard API exists in this space for hobby farms. Building integrations with niche software adds complexity for near-zero audience. | Export data as CSV/JSON. Users can import elsewhere manually. |
| **OAuth/social login** | Explicitly out of scope. Unnecessary for single-user system. Adds dependency on external providers. | No auth, or simple password/token if needed. |
| **Predictive analytics / AI forecasting** | "You'll have 5 eggs tomorrow" -- not useful, not accurate, and the data volume from a small flock is far too small for meaningful predictions. | Show historical trends. Let the human interpret. |

---

## Feature Dependencies

```
Egg Detection (YOLO model) --> Size Classification (needs bounding box dimensions)
Egg Detection --> De-duplication (needs position tracking across frames)
Egg Detection --> Daily Count (needs detection events to count)
Egg Detection --> Event Log (needs detection events to log)
De-duplication --> Daily Count (count depends on correctly de-duplicated detections)
Daily Count --> Historical Data (daily totals feed into history)
Historical Data --> Weekly/Monthly Reports (aggregation of historical data)
Historical Data --> Laying Pattern Analysis (time-series analysis)
WebSocket Connection --> Real-time Dashboard Updates (transport layer)
Remote Access Setup --> Dashboard Accessible from Phone (network layer)
Daily Count + Size Classification --> Dashboard Display (data to render)
System Health (heartbeat) --> Stale Data Warning (depends on heartbeat)

Detection Event --> Snapshot on Detection (triggered by detection)
Collection Tracking --> "In Box" Counter (subtraction from daily count)
```

Key dependency chains:

1. **Detection chain:** YOLO Model --> Detection --> De-duplication --> Counting --> Display
2. **Data chain:** Detection Events --> Storage --> History --> Trends/Reports
3. **Delivery chain:** WebSocket --> Real-time Updates --> Dashboard --> Remote Access

The detection chain is the critical path. Everything downstream depends on reliable, de-duplicated egg detection.

---

## MVP Recommendation

Prioritize in this order:

1. **Egg detection with YOLO** -- the foundation. Nothing works without it. Train or fine-tune a model that detects eggs in nest box images with high recall (missing an egg is worse than a false positive at this stage).

2. **De-duplication logic** -- immediately after detection. Without this, the count is meaningless. Track egg positions across frames; only increment count when a genuinely new egg appears.

3. **Size classification** -- classify detected eggs by bounding box dimensions relative to a calibration reference. The existing object_measurer.py demonstrates the approach (A4 paper calibration). For nest box use, a fixed camera distance may provide adequate calibration without a reference object.

4. **Daily count with dashboard** -- the minimum useful output. Today's egg count by size, displayed on a mobile-responsive web page.

5. **WebSocket real-time updates** -- push detection events from Pi to dashboard so counts update live.

6. **System health indicator** -- heartbeat so user knows the system is running when checking remotely.

7. **Remote access** -- expose dashboard beyond local network via tunnel or VPN.

8. **Historical data and trends** -- persistent storage, charts over time.

**Defer to post-MVP:**
- Event log with timestamps: Low effort but not critical for initial value
- Collection tracking: Nice but requires user interaction model
- Snapshots on detection: Storage management complexity
- Weekly reports: Needs historical data to accumulate first
- Laying pattern analysis: Needs weeks of data before useful
- Multi-camera support: Scope expansion, validate single-box first
- Model retraining pipeline: Training happens offline for v1
- Export: No data to export until history exists

---

## Complexity Assessment by Feature Area

### Detection (High complexity)
- YOLO model selection and optimization for Pi 5 (YOLOv8n or YOLO11n for edge)
- Training data collection and annotation (eggs in nest boxes, various lighting)
- Inference performance tuning (target: at least 5 FPS for reliable detection)
- Handling variable lighting in nest boxes (shadows, morning vs. evening)

### De-duplication (High complexity)
- This is the hardest non-obvious problem in the system
- Must distinguish "same egg, new frame" from "new egg appeared"
- Approaches: position-based tracking (IoU of bounding boxes across frames), background subtraction to detect change, or simple "count only increases when new region occupied"
- Edge cases: eggs removed (collected), hen sitting on eggs (occluded), eggs rolling

### Size Classification (Medium complexity)
- Defining size boundaries (USDA: Jumbo > 70g, XL > 63g, L > 56g, M > 49g, S > 42g -- but these are by weight, not visual size)
- Visual size must correlate dimensions to weight categories approximately
- Camera distance calibration matters enormously
- Fixed camera mount simplifies this considerably (known distance = known scale)

### Dashboard (Medium complexity)
- Web framework selection (lightweight: plain HTML/JS with WebSocket, or small framework)
- Real-time updates via WebSocket client
- Chart library for trends
- Mobile-responsive layout
- Must feel snappy on a phone over cellular connection

### Infrastructure (Medium complexity)
- Pi 5 runs detection loop, serves WebSocket, optionally hosts dashboard
- Or: Pi pushes data to a lightweight cloud backend that hosts dashboard
- Remote access: Cloudflare Tunnel (free, reliable) or Tailscale (easy, peer-to-peer)
- Database for historical data (SQLite on Pi is simplest; hosted DB if using cloud backend)

---

## Sources

- Project requirements: `.planning/PROJECT.md`
- Existing codebase analysis: `camera_scanner.py`, `object_measurer.py`, `capture_images.py`
- Domain knowledge of YOLO object detection, Raspberry Pi ML inference, IoT dashboard patterns, and WebSocket architectures (confidence: MEDIUM -- based on training data, web search unavailable for verification)
- USDA egg size classifications are well-established standards (confidence: HIGH)
- Note: The reference thesis (`ref/AZUR-THESIS-OUTLINEFOR-AI-CHECKING.pdf`) could not be read due to tooling limitations. It may contain additional domain context worth reviewing manually.
