# Project Research Summary

**Project:** Egg Counter -- Real-time egg counting and size classification on Raspberry Pi 5
**Domain:** Edge computer vision with IoT real-time web dashboard
**Researched:** 2026-03-19
**Confidence:** MEDIUM-HIGH

## Executive Summary

This is an edge computer vision system: a Raspberry Pi 5 runs continuous YOLO inference on a USB camera feed, detects and counts eggs as they appear in a nest box, classifies them by visual size, and pushes live updates to a mobile-friendly web dashboard accessible remotely via Cloudflare Tunnel. Experts build this class of system as a self-contained monolith on the Pi -- a single Python process that owns detection, persistence, and web serving. No cloud backend, no microservices, no build toolchain. The recommended stack is YOLO11n (nano) exported to NCNN format for ARM inference, FastAPI with native WebSocket support, SQLite for persistence, and vanilla JS with Chart.js for the dashboard.

The single most critical decision is **model export format**: YOLO11n in PyTorch format runs at 0.5-2 FPS on the Pi; the same model exported to NCNN format runs at 15-30 FPS. Everything else is downstream of getting this right. The second most critical decision is **de-duplication**: eggs sit in the nest box for hours, so YOLO will detect the same egg hundreds of times per session. Without stateful tracking (Ultralytics built-in ByteTrack), a system that "works" will count 6 eggs as 600 within minutes. These two problems -- model format and de-duplication -- must be solved in Phase 1 before any web or dashboard work begins.

The main risks are training data domain gap (model trained on clean studio images fails in the real nest box environment), SD card wear from continuous writes, and WebSocket connection unreliability on mobile. All three are well-understood and preventable with disciplined architecture choices: collect training data from the actual deployment environment, write persistent data to a USB SSD rather than the SD card, and implement WebSocket reconnection with exponential backoff from day one.

## Key Findings

### Recommended Stack

The full stack runs on Raspberry Pi OS 64-bit (Bookworm Lite) with Python 3.11 or 3.12. The 64-bit OS is mandatory -- NCNN and modern numpy require it. The inference pipeline is Ultralytics YOLO11n exported to NCNN format, which is the only format that delivers adequate frame rate on the Pi 5 Cortex-A76 CPU. OpenCV headless handles camera capture at a controlled 2-5 FPS (not the camera's native 30 FPS -- inference cannot keep up and eggs do not move fast enough to require it). FastAPI with Uvicorn provides both the REST API and native WebSocket support in a single async process, eliminating the need for Socket.IO or a separate web server. SQLite with WAL mode handles persistence with zero operational overhead. The dashboard is static HTML/CSS/JS served from the Pi itself with Chart.js for trend charts. Cloudflare Tunnel exposes the dashboard as a stable HTTPS URL without port forwarding or a VPS.

**Core technologies:**
- YOLO11n (Ultralytics) + NCNN export: Object detection and size classification -- only format that achieves real-time FPS on ARM CPU
- OpenCV headless (>=4.9): USB camera capture via V4L2, 2-5 FPS controlled rate
- FastAPI + Uvicorn (>=0.115): Async HTTP + WebSocket server -- native WebSocket eliminates Socket.IO complexity
- aiosqlite + SQLite WAL: Persistent storage -- zero-config, crash-safe, no server process
- Vanilla JS + Chart.js: Dashboard -- no build step, served as static files, mobile-responsive
- systemd: Process management -- auto-restart, boot-start, journal logging
- Cloudflare Tunnel: Remote access -- free HTTPS URL, no port forwarding, WebSocket-compatible
- Python venv on USB SSD: All persistent I/O off the SD card to prevent wear

### Expected Features

The detection chain is the critical path for all features. YOLO model leads to de-duplication which leads to counting which leads to everything else. Building the dashboard before the detection chain is reliable produces a beautiful dashboard showing meaningless numbers.

**Must have (table stakes):**
- Egg detection with YOLO model -- the core product; nothing works without it
- De-duplication (stateful tracking) -- without this the count is wrong by orders of magnitude
- Size classification (S/M/L/XL from bounding box dimensions) -- second core promise of the project
- Daily count display by size -- minimum useful output, readable at a glance
- Real-time WebSocket push updates -- stated requirement; polling is inadequate for live monitoring
- System health indicator / heartbeat -- user must know if the Pi is offline when checking remotely
- Remote access via Cloudflare Tunnel -- dashboard must work from phone outside local network
- Historical data and trend charts -- without history the dashboard is just a counter
- Mobile-responsive layout -- primary use case is checking from phone

**Should have (differentiators for v1+ or post-MVP):**
- Detection event log with timestamps -- "egg appeared at 10:32 AM (large)"
- Collection tracking -- "I collected 6 eggs" button; shows produced vs. collected vs. in-box
- Lighting/image quality warnings -- proactive warning when frame is too dark for reliable detection
- Snapshot on detection -- cropped image saved with each event, viewable in event log
- Configurable daily reset time -- farms start at dawn, not midnight

**Defer (v2+):**
- Push notifications -- adds service worker complexity, deferred per PROJECT.md
- Weekly/monthly production reports -- needs data to accumulate before useful
- Laying pattern analysis (time-of-day heatmap) -- needs weeks of data
- Multi-camera / multi-box support -- scope expansion, validate single-box first
- Model retraining pipeline with annotation UI -- training happens offline in v1
- Export data (CSV/JSON) -- no data to export until history exists

**Explicit anti-features (never build):**
- Live camera feed streaming -- out of scope per PROJECT.md; bandwidth and privacy concerns
- Multi-user accounts / OAuth -- single-user system, unnecessary complexity
- Egg weight measurement -- requires hardware scale, explicitly out of scope
- Egg quality/defect detection -- substantially harder ML problem, different product

### Architecture Approach

The architecture is a three-layer monolith on the Pi: detection pipeline, data persistence, and web server run as a single async Python process. The detection loop and FastAPI web server share the same asyncio event loop -- the detection loop yields between frames, allowing the web server to handle incoming requests without blocking. Data flows from camera through YOLO inference through ByteTrack object tracker through an event processor that writes to SQLite and broadcasts via WebSocket to connected browsers. Cloudflare Tunnel runs as a separate systemd service proxying to FastAPI's port. There is no cloud component; the Pi is the server.

**Major components:**
1. Camera Capture (OpenCV FrameGrabber) -- controlled 2-5 FPS frame acquisition with camera reconnect loop
2. Detection Pipeline (YOLO11n NCNN) -- inference at 640x640, returns bounding boxes with class and confidence
3. Object Tracker (Ultralytics ByteTrack) -- assigns persistent IDs across frames; new ID = new egg event
4. Event Processor -- deduplicates, writes to SQLite, broadcasts via WebSocket, implements 5-min cooldown
5. SQLite Database -- two tables: `egg_events` (raw events) and `daily_summaries` (aggregated); WAL mode on USB SSD
6. FastAPI Web Server -- REST endpoints for today/history/events/status, WebSocket hub for broadcast
7. Dashboard (static HTML/JS) -- Chart.js trend charts, WebSocket client with exponential backoff reconnection
8. Cloudflare Tunnel -- systemd service exposing localhost:8000 as permanent HTTPS URL

### Critical Pitfalls

1. **Using PyTorch .pt model format on the Pi** -- export to NCNN before any Pi testing; NCNN is 3-8x faster on ARM; PyTorch gives 0.5-2 FPS which is unusable. Benchmark on actual hardware in Phase 1.

2. **Double-counting stationary eggs** -- use `model.track()` (ByteTrack) instead of `model.predict()` from day one; maintain a `seen_track_ids` set; add a minimum 3-5 frame persistence threshold before counting.

3. **Training on studio images, deploying in a dirty nest box** -- collect 100+ annotated images from the actual deployment environment with the actual camera; budget 2-3 retraining cycles; augment with brightness variation, noise, and partial occlusion.

4. **SD card death from continuous writes** -- all SQLite writes, logs, and swap must go to a USB SSD; SD card should be as close to read-only as possible after boot; use SQLite WAL mode.

5. **WebSocket treated as always-on** -- implement exponential backoff reconnection, heartbeat ping/pong, visible connection status indicator, and REST state fetch on reconnect; use `visibilitychange` event to trigger reconnect when phone wakes.

## Implications for Roadmap

Based on research, the architecture file explicitly defines the build order. Phase structure follows component dependencies: the detection chain must be validated standalone before any web layer is built, persistence must exist before the dashboard can show anything meaningful, and remote access is operational polish on a working system.

### Phase 1: Detection Pipeline (Standalone)

**Rationale:** The detection chain is the critical path for the entire project. De-duplication (the hardest non-obvious problem), model format (NCNN vs PyTorch), and inference frame rate are all architectural decisions that cannot be changed later without a rewrite. These must be solved before building anything else. Validate that YOLO11n NCNN can actually detect and count eggs in the real nest box environment before committing to the rest of the architecture.

**Delivers:** A CLI tool that prints "New egg: large (0.92 conf)" to stdout when a real new egg appears in the camera frame. No web, no database -- just correct detection and counting.

**Addresses:** Egg detection, size classification, de-duplication (from FEATURES.md must-haves)

**Avoids:**
- Pitfall 1 (PyTorch format): Export to NCNN immediately
- Pitfall 2 (double-counting): Implement ByteTrack tracking from the first line of counting logic
- Pitfall 3 (domain gap): Test against actual nest box images, not stock datasets
- Pitfall 6 (camera warm-up): Discard first 30 frames on startup
- Pitfall 8 (inference on every frame): Design 2-5 FPS capture rate from the start

**Research flag:** NEEDS RESEARCH -- actual NCNN performance benchmarks on Pi 5 should be verified against current Ultralytics documentation; YOLO11n naming convention should be confirmed; ByteTrack API syntax should be verified against current Ultralytics version.

### Phase 2: Data Persistence

**Rationale:** Once detection is correct, the next step is making it durable. Persistence must exist before the dashboard because the dashboard has nothing to show without stored data. SQLite schema and WAL mode must be established before writes begin -- retrofitting WAL mode onto an existing database with live data is risky.

**Delivers:** Eggs are counted, stored in SQLite on USB SSD, and survive Pi reboots. Daily count is reconstructed from database on startup (startup reconciliation).

**Addresses:** Historical data storage, daily count persistence, daily reset logic (from FEATURES.md)

**Uses:** aiosqlite, SQLite WAL mode, USB SSD mount

**Implements:** SQLite Database + Event Processor components from architecture

**Avoids:**
- Pitfall 4 (SD card death): USB SSD for all persistent I/O from the start
- Pitfall 9 (no persistence on reboot): Write events immediately on detection, load state on startup
- Pitfall 11 (power loss): WAL mode enabled before any data is written
- Pitfall 13 (timezone confusion): Configure local timezone, define "egg day" reset time, store UTC display local

**Research flag:** Standard patterns -- SQLite WAL mode, aiosqlite with FastAPI, and systemd are all well-documented. Skip research-phase for this phase.

### Phase 3: Web Dashboard

**Rationale:** With detection working and data persisted, the web layer simply reads from SQLite and pushes events via WebSocket. FastAPI connects the detection output to the browser. This phase produces the first user-facing deliverable: a working dashboard on the local network.

**Delivers:** Working dashboard on local network showing live egg count, size breakdown, historical trend chart, and system health indicator.

**Addresses:** Real-time WebSocket updates, daily count display, historical charts, system health indicator, mobile-responsive layout (from FEATURES.md must-haves)

**Uses:** FastAPI, Uvicorn, Starlette WebSocket, Chart.js, vanilla HTML/CSS/JS

**Implements:** FastAPI Web Server + Dashboard UI + WebSocket Manager components

**Avoids:**
- Pitfall 5 (WebSocket always-on assumption): Implement reconnection, heartbeat, and state sync on reconnect from the first WebSocket line
- Pitfall 14 (overengineered frontend): Vanilla JS + Chart.js from CDN; no React, no build step
- Anti-pattern 2 (polling instead of push): WebSocket from day one, no setInterval polling

**Research flag:** Standard patterns -- FastAPI WebSocket, Chart.js, and vanilla JS WebSocket API are all well-documented with stable APIs. Skip research-phase.

### Phase 4: Remote Access and Hardening

**Rationale:** Cloudflare Tunnel, systemd services, logging, and graceful error recovery are operational polish that wrap the working system for production reliability. These should come last because they depend on the application being complete and stable.

**Delivers:** Production-ready system accessible from phone anywhere, auto-restarts on crash, auto-starts on boot, recovers gracefully from camera disconnection.

**Addresses:** Remote phone access, system health monitoring (from FEATURES.md must-haves)

**Uses:** Cloudflare Tunnel (cloudflared), systemd, journald logging, python-dotenv for config

**Implements:** Tunnel + systemd components; graceful degradation pattern from architecture

**Avoids:**
- Pitfall 10 (direct internet exposure): Cloudflare Tunnel, never port forwarding
- Pitfall 4 (hardware): USB SSD final verification, temperature monitoring
- Pitfall 12 (thermal throttling): Active cooler, ventilated enclosure, temperature alerts

**Research flag:** Cloudflare Tunnel free tier setup for Raspberry Pi may need verification against current documentation (terms and setup steps can change). Otherwise standard patterns.

### Phase Ordering Rationale

- **Detection before everything:** YOLO detection + tracking is the critical path. Every other feature depends on correct, de-duplicated egg counts. Validate this risk first.
- **Persistence before dashboard:** The dashboard needs data. Building the UI before the data layer exists means building against mocked data that may not match the real schema.
- **Dashboard before remote access:** Cloudflare Tunnel can only expose a working application. Test thoroughly on local network before adding the remote access layer.
- **Pitfall alignment:** Phases 1 and 2 address the 5 critical pitfalls. Phases 3 and 4 address the moderate pitfalls. No critical pitfall is deferred to a late phase.
- **Dependency chain from FEATURES.md:** Detection -> De-duplication -> Counting -> Display -> Remote Access maps directly to Phases 1 through 4.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1 (Detection Pipeline):** NCNN export API and performance benchmarks should be verified against current Ultralytics documentation. YOLO11 naming (vs YOLOv8) and ByteTrack API syntax should be confirmed. The real-world inference speed on Pi 5 may differ from training data estimates.
- **Phase 4 (Remote Access):** Cloudflare Tunnel free tier setup steps and any current limitations should be verified. The domain requirement (Cloudflare must be DNS provider) may need alternatives documented.

Phases with standard patterns (skip research-phase):
- **Phase 2 (Persistence):** SQLite WAL mode, aiosqlite, and systemd unit files are stable, well-documented technologies with no edge cases specific to this project.
- **Phase 3 (Dashboard):** FastAPI WebSocket, Chart.js, and vanilla JS are mature with stable APIs and extensive documentation. The reconnection pattern is well-established.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM-HIGH | Core technologies (Ultralytics, FastAPI, SQLite) are stable and well-established. Specific NCNN benchmark numbers on Pi 5 should be verified on actual hardware. YOLO11 naming should be confirmed against current Ultralytics docs. |
| Features | MEDIUM | Feature set derived from project requirements and domain knowledge. Anti-features and deferral decisions are well-reasoned but should be validated with the project owner. |
| Architecture | MEDIUM-HIGH | Monolith-on-Pi pattern is established and appropriate for the scale. Async detection loop + FastAPI is a known pattern. Specific API syntax should be verified against current library versions. |
| Pitfalls | HIGH | Critical pitfalls (model format, double-counting, domain gap, SD card, WebSocket reliability) are well-documented across many RPi CV deployments. These are reliable warnings from broad community experience. |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **Actual hardware benchmarks:** NCNN inference speed on Pi 5 is estimated at 15-30 FPS for YOLO11n nano. This must be measured on the actual target hardware in Phase 1. If it falls short, the architecture may need adjustment (lower FPS, smaller input resolution, or motion-gating inference).
- **Size classification accuracy:** Visual size classification (S/M/L/XL from bounding box dimensions) will have lower accuracy than weight-based methods. The project must decide acceptable accuracy and whether 4 categories vs 3 is achievable visually. This should be validated during Phase 1 model training.
- **Training data availability:** The project requires annotated images of eggs in the actual nest box. If the nest box is not yet set up or does not have eggs to photograph, Phase 1 model training cannot begin. This should be assessed before planning starts.
- **Domain name requirement:** Cloudflare Tunnel in its standard form requires a domain name (approximately $10/year). If no domain is available, the alternative (Tailscale Funnel) should be planned for Phase 4.
- **Thesis reference:** `.planning/research/` notes that `ref/AZUR-THESIS-OUTLINEFOR-AI-CHECKING.pdf` could not be read. This may contain domain context relevant to egg classification standards or detection methodology.

## Sources

### Primary (HIGH confidence)
- Ultralytics documentation (training data) -- YOLO11 architecture, NCNN export, ByteTrack integration, Raspberry Pi deployment guide
- FastAPI documentation (training data) -- WebSocket support, Starlette integration, async lifecycle
- Cloudflare Tunnel documentation (training data) -- setup, free tier, WebSocket compatibility
- SQLite documentation (training data) -- WAL mode, crash recovery, performance characteristics

### Secondary (MEDIUM confidence)
- Ultralytics Raspberry Pi benchmark data (training data) -- NCNN vs ONNX vs PyTorch performance comparison on Pi 5
- Community experience with RPi CV deployments (training data) -- common failure modes, thermal issues, SD card wear patterns
- Existing project codebase analysis -- `camera_scanner.py`, `object_measurer.py`, `capture_images.py` inform the existing approach and calibration methodology
- USDA egg size classification standards -- weight-based standards used as reference for visual size category definitions

### Tertiary (LOW confidence -- verify before implementation)
- Exact NCNN inference speed numbers on Pi 5 -- estimated from training data, must be measured on actual hardware
- Cloudflare Tunnel current free tier terms -- may have changed; verify before Phase 4 planning
- YOLO11 vs YOLOv11 naming -- Ultralytics renamed in late 2024; confirm current package naming
- NCNN ARM64 pip wheel availability -- Ultralytics may handle this automatically; verify during Phase 1 setup

---
*Research completed: 2026-03-19*
*Ready for roadmap: yes*
