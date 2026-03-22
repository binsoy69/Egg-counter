# Phase 1: Detection Pipeline - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

YOLO-based egg detection, ByteTrack de-duplication, and size classification running on Raspberry Pi 5 with USB camera. User can run the detection process and see new egg notifications with size classification. Each physical egg is counted exactly once. Detection events are logged with timestamp and size.

</domain>

<decisions>
## Implementation Decisions

### Size Classification Approach
- **D-01:** Try both approaches and compare accuracy:
  1. **Bounding box ratio method** — use egg bbox height relative to nest box width (nest box always in frame, known dimensions) to estimate real size and map to small/medium/large/jumbo
  2. **Multi-class YOLO model** — train YOLO with 4 classes (egg-small, egg-medium, egg-large, egg-jumbo) so the model directly outputs size
- **D-02:** Whichever approach is more accurate wins, even if it requires more annotation work
- **D-03:** Nest box itself serves as the reference object for the ratio method (always visible, known dimensions)

### De-duplication & Counting Logic
- **D-04:** Zone-based trigger — define a nest box region in the frame. An egg is counted when it first appears in the zone and stays stable for 3 seconds
- **D-05:** ByteTrack assigns track IDs. Once a track ID is counted, it is never re-counted even if temporarily occluded
- **D-06:** During occlusion (hen sitting on eggs), keep last known count — don't subtract eggs just because they're hidden
- **D-07:** Each egg is counted independently with its own track ID and timestamp, even if multiple eggs appear simultaneously
- **D-08:** On camera/system restart, re-detect visible eggs and treat them as already-counted to avoid double-counting
- **D-09:** Egg removal is manual (owner collects all at once). System should log removal events when all tracked eggs leave the zone
- **D-10:** Count resets when eggs are collected (ties into Phase 3 "collected" action). For Phase 1, the pipeline logs events — reset logic lives in persistence/dashboard layers
- **D-11:** Daylight-only detection — skip detection at night to save resources and avoid false positives

### Zone Configuration
- **D-12:** One-time setup tool — a script where user draws the nest box zone rectangle on a camera frame, saved to a config file

### Detection Output & Logging
- **D-13:** Structured JSON lines format (.jsonl) — one JSON object per line per event
- **D-14:** Event types: `egg_detected` and `eggs_collected`
- **D-15:** Each egg event includes: timestamp, track_id, size classification, confidence score, bounding box coordinates, size method used and raw measurement
- **D-16:** Human-readable summary also printed to stdout in real-time (e.g., "New egg #7 — large")
- **D-17:** Daily log file rotation (e.g., `eggs-2026-03-22.jsonl`)
- **D-18:** Egg events only in logs — no diagnostic/system health info mixed in

### Claude's Discretion
- YOLO confidence threshold default (sensible default, made configurable)
- Log file storage path (sensible default, configurable)
- Additional useful fields in event JSON beyond those specified
- Technical details of ByteTrack configuration
- Handling of edge cases not explicitly discussed (e.g., partial visibility, unusual angles)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

No external specs — requirements are fully captured in decisions above and the following project files:

### Project requirements
- `.planning/REQUIREMENTS.md` — DET-01 through DET-04 define detection requirements for this phase
- `.planning/ROADMAP.md` §Phase 1 — Phase goal, success criteria, and dependency info
- `.planning/PROJECT.md` — Hardware constraints (Pi 5, USB camera), model choice (YOLO11n), visual estimation approach

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `capture_images.py` — Image capture tool for dataset collection (OpenCV, 1280x720). Can be used/extended for collecting training data
- `camera_scanner.py` — Camera diagnostic tool. Useful for identifying the correct camera index on the Pi
- `object_measurer.py` — Contains `ImagePreprocessor` class with CLAHE-based lighting normalization that could inform preprocessing choices for variable nest box lighting

### Established Patterns
- OpenCV is already used throughout for camera access and image processing
- All existing code uses Python with cv2
- Current code targets Windows (DirectShow) — production will need Linux/Pi camera backend

### Integration Points
- `captured_images/` folder exists for training data collection
- Phase 2 (Data Persistence) will consume the .jsonl log files produced by this phase
- Phase 3 (Web Dashboard) will need real-time events — the detection pipeline should be structured to support future WebSocket integration

</code_context>

<specifics>
## Specific Ideas

- User wants to benchmark both size classification approaches (bbox ratio vs multi-class YOLO) to pick the more accurate one
- Nest box is the calibration reference — its known physical dimensions provide the scale for the ratio method
- Eggs are always collected all at once (not partial), which simplifies the collection detection logic
- The 3-second stability threshold was chosen for quick registration since hens don't linger near the box before laying

</specifics>

<deferred>
## Deferred Ideas

- Configurable daily reset time (dawn vs midnight) — deferred to v2 per DET-06
- System health/diagnostic logging — explicitly excluded from egg event logs, could be a separate monitoring concern
- Night/IR detection — not needed, hens lay during daylight

</deferred>

---

*Phase: 01-detection-pipeline*
*Context gathered: 2026-03-22*
