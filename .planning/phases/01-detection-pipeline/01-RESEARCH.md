# Phase 1: Detection Pipeline - Research

**Researched:** 2026-03-22
**Domain:** YOLO object detection, ByteTrack multi-object tracking, edge inference on Raspberry Pi 5
**Confidence:** HIGH

## Summary

This phase builds a real-time egg detection pipeline using Ultralytics YOLO with ByteTrack tracking on a Raspberry Pi 5 with USB camera. The Ultralytics ecosystem provides a unified Python API that handles detection, tracking, and model export in a single package. ByteTrack is built into ultralytics and requires no additional installation -- it is enabled by passing `tracker="bytetrack.yaml"` to the `model.track()` method.

YOLO26 (released January 2026) is the current recommended model for Raspberry Pi edge deployment, offering ~15% faster inference than YOLO11n while providing higher mAP. It features NMS-free architecture (eliminating a major export bottleneck) and improved small-object detection. NCNN is the optimal export format for Pi 5, reducing inference from ~525ms (PyTorch) to ~94ms per frame at 640px input.

**Primary recommendation:** Use YOLO26n (nano) with NCNN export, ByteTrack for de-duplication, and a custom zone-based counting pipeline. Train on the user's own nest box images. Size classification should start with the bounding-box-ratio method (using the nest box as reference), with multi-class YOLO as the comparison approach.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01/D-02:** Try both size classification approaches (bbox ratio method vs multi-class YOLO) and compare accuracy
- **D-03:** Nest box serves as reference object for ratio method
- **D-04:** Zone-based trigger with 3-second stability threshold for counting
- **D-05:** ByteTrack assigns track IDs; once counted, never re-counted
- **D-06:** During occlusion (hen sitting), keep last known count
- **D-07:** Each egg counted independently with own track ID and timestamp
- **D-08:** On restart, re-detect visible eggs and treat as already-counted
- **D-09:** Egg removal is manual; log removal when all tracked eggs leave zone
- **D-10:** Count resets tied to Phase 3 "collected" action; Phase 1 just logs events
- **D-11:** Daylight-only detection to save resources
- **D-12:** One-time zone setup tool (user draws nest box rectangle, saved to config)
- **D-13:** Structured JSON lines format (.jsonl)
- **D-14:** Event types: `egg_detected` and `eggs_collected`
- **D-15:** Event fields: timestamp, track_id, size classification, confidence, bbox, size method, raw measurement
- **D-16:** Human-readable stdout summary in real-time
- **D-17:** Daily log rotation (e.g., `eggs-2026-03-22.jsonl`)
- **D-18:** Egg events only in logs -- no diagnostic/system health info

### Claude's Discretion
- YOLO confidence threshold default (sensible default, made configurable)
- Log file storage path (sensible default, configurable)
- Additional useful fields in event JSON beyond those specified
- Technical details of ByteTrack configuration
- Handling of edge cases not explicitly discussed

### Deferred Ideas (OUT OF SCOPE)
- Configurable daily reset time (dawn vs midnight) -- deferred to v2
- System health/diagnostic logging
- Night/IR detection

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DET-01 | Detect eggs in nest box using YOLO11n model on Raspberry Pi 5 | YOLO26n (successor to YOLO11n) with NCNN export; ultralytics 8.4.24 provides unified API for training, export, and inference |
| DET-02 | De-duplicate detections so each physical egg is counted exactly once | ByteTrack built into ultralytics; zone-based counting with track ID registry; 3-second stability threshold |
| DET-03 | Classify egg size (small, medium, large, jumbo) via visual estimation | Two approaches: bbox ratio method (nest box as reference) and multi-class YOLO training; compare and pick winner |
| DET-04 | Each detection logged with timestamp and size classification | JSONL structured logging with daily rotation; stdout human-readable summary |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| ultralytics | 8.4.24 | YOLO26 detection + ByteTrack tracking + NCNN export | Single package for entire detection pipeline; official Ultralytics library |
| opencv-python-headless | 4.x | Camera capture, frame processing, zone drawing tool | Already used in project; headless variant for Pi (no GUI dependencies) |
| numpy | 1.x | Array operations, bbox calculations | Required by ultralytics and opencv |
| astral | 3.x | Sunrise/sunset calculation for daylight-only detection | Lightweight, no external API needed; calculates from lat/lon |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| supervision | 0.27.0 | Zone detection, annotation visualization during development | Optional -- useful for zone-based counting utilities and debugging visualization. Can be skipped if implementing zone logic manually |
| pyyaml | 6.x | Config file parsing (zone config, ByteTrack params) | Already a dependency of ultralytics |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| YOLO26n | YOLO11n | YOLO11n still works fine, but YOLO26n is ~15% faster on Pi 5 with higher mAP. Use YOLO26n. |
| ByteTrack | BoT-SORT | BoT-SORT adds ReID model overhead. ByteTrack is simpler, faster, and sufficient for static-camera egg counting |
| NCNN export | ONNX export | NCNN is specifically optimized for ARM CPUs. ONNX on Pi 5 gets ~147ms vs NCNN ~94ms |
| supervision zones | Custom zone logic | supervision adds a dependency but provides well-tested PolygonZone. For this project, a simple rectangle check is trivial to hand-roll |

**Installation (development machine for training):**
```bash
pip install ultralytics[export] astral
```

**Installation (Raspberry Pi 5 for inference):**
```bash
pip install ultralytics[export] astral opencv-python-headless
# Then export model to NCNN:
yolo export model=best.pt format=ncnn
```

**Version verification:** ultralytics 8.4.24 confirmed on PyPI (released 2026-03-19). supervision 0.27.0 confirmed on PyPI (released 2026-03-14). astral 3.2 on PyPI.

## Architecture Patterns

### Recommended Project Structure
```
src/
  egg_counter/
    __init__.py
    config.py          # Config loading (zone, thresholds, location)
    detector.py         # YOLO model wrapper
    tracker.py          # ByteTrack + de-duplication logic
    size_classifier.py  # Size classification (both methods)
    zone.py             # Zone definition and containment check
    logger.py           # JSONL event logging with rotation
    scheduler.py        # Daylight-only scheduling
    pipeline.py         # Main detection loop orchestrating all components
    cli.py              # Entry point with argparse
config/
    zone.json           # Nest box zone rectangle (from setup tool)
    settings.yaml       # Thresholds, camera index, location, log path
models/
    best_ncnn_model/    # Exported NCNN model directory
tools/
    setup_zone.py       # One-time zone configuration tool
    capture_images.py   # Existing image capture tool (moved/linked)
logs/
    eggs-YYYY-MM-DD.jsonl  # Daily egg event logs
data/
    dataset/            # Training images and labels (YOLO format)
        images/
            train/
            val/
        labels/
            train/
            val/
        data.yaml       # Dataset configuration
tests/
    test_zone.py
    test_tracker.py
    test_size_classifier.py
    test_logger.py
    conftest.py
```

### Pattern 1: Frame Processing Pipeline
**What:** Main detection loop that captures frames, runs detection, tracks, classifies, and logs
**When to use:** The core runtime loop
**Example:**
```python
# Source: ultralytics docs - tracking mode
from ultralytics import YOLO
import cv2

model = YOLO("models/best_ncnn_model")
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

counted_ids = set()  # Track IDs already counted

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    results = model.track(frame, persist=True, tracker="bytetrack.yaml")

    if results[0].boxes.id is not None:
        track_ids = results[0].boxes.id.int().cpu().tolist()
        boxes = results[0].boxes.xyxy.cpu().numpy()
        confs = results[0].boxes.conf.cpu().tolist()

        for tid, box, conf in zip(track_ids, boxes, confs):
            if tid not in counted_ids and is_in_zone(box, zone_config):
                # Egg is in zone and not yet counted
                size = classify_size(box, zone_config)
                log_event(tid, size, conf, box)
                counted_ids.add(tid)
                print(f"New egg #{len(counted_ids)} -- {size}")
```

### Pattern 2: Zone-Based Containment Check
**What:** Check if a bounding box center falls within the defined nest box zone
**When to use:** Filtering detections to only count eggs inside the nest box
**Example:**
```python
def is_in_zone(box_xyxy, zone_rect):
    """Check if bbox center is inside the nest box zone."""
    x1, y1, x2, y2 = box_xyxy
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    zx1, zy1, zx2, zy2 = zone_rect
    return zx1 <= cx <= zx2 and zy1 <= cy <= zy2
```

### Pattern 3: Bounding Box Ratio Size Classification
**What:** Estimate real egg size using the nest box as a known-dimension reference
**When to use:** D-01 bbox ratio method
**Example:**
```python
# Nest box width is known (e.g., 300mm)
# Zone rectangle width in pixels is known from setup
def classify_by_ratio(egg_bbox, zone_rect, nest_box_width_mm=300):
    """Classify egg size using nest box as reference."""
    _, _, zx2, _ = zone_rect
    zx1, _, _, _ = zone_rect
    zone_width_px = zx2 - zx1
    px_per_mm = zone_width_px / nest_box_width_mm

    ex1, ey1, ex2, ey2 = egg_bbox
    egg_height_px = ey2 - ey1
    egg_height_mm = egg_height_px / px_per_mm

    # USDA egg size by height (approximate visual height):
    # Jumbo: > 63mm, Large: 56-63mm, Medium: 50-56mm, Small: < 50mm
    if egg_height_mm > 63:
        return "jumbo"
    elif egg_height_mm > 56:
        return "large"
    elif egg_height_mm > 50:
        return "medium"
    else:
        return "small"
```

### Pattern 4: JSONL Event Logging
**What:** Structured event logging with daily rotation
**When to use:** Every egg detection and collection event
**Example:**
```python
import json
from datetime import datetime
from pathlib import Path

def log_event(log_dir, event):
    """Append a JSON event to today's log file."""
    today = datetime.now().strftime("%Y-%m-%d")
    path = Path(log_dir) / f"eggs-{today}.jsonl"
    with open(path, "a") as f:
        f.write(json.dumps(event) + "\n")

# Event structure for egg_detected:
event = {
    "type": "egg_detected",
    "timestamp": "2026-03-22T14:32:05.123Z",
    "track_id": 7,
    "size": "large",
    "confidence": 0.89,
    "bbox": [120, 80, 210, 190],
    "size_method": "bbox_ratio",
    "raw_measurement_mm": 58.3,
    "frame_number": 4521
}
```

### Pattern 5: Stability Timer for Counting
**What:** Only count an egg after it remains in-zone for 3 seconds
**When to use:** D-04 zone-based trigger
**Example:**
```python
from time import time

pending_tracks = {}  # track_id -> first_seen_time
STABILITY_SECONDS = 3

def check_stability(track_id, in_zone):
    """Track must be in zone for STABILITY_SECONDS before counting."""
    now = time()
    if in_zone:
        if track_id not in pending_tracks:
            pending_tracks[track_id] = now
        elif now - pending_tracks[track_id] >= STABILITY_SECONDS:
            del pending_tracks[track_id]
            return True  # Stable -- count it
    else:
        pending_tracks.pop(track_id, None)  # Left zone, reset timer
    return False
```

### Pattern 6: Daylight Scheduling
**What:** Use astral to compute sunrise/sunset and skip detection at night
**When to use:** D-11 daylight-only detection
**Example:**
```python
from astral import LocationInfo
from astral.sun import sun
from datetime import datetime, date

def is_daylight(lat, lon):
    """Check if current time is between sunrise and sunset."""
    loc = LocationInfo(latitude=lat, longitude=lon)
    s = sun(loc.observer, date=date.today())
    now = datetime.now(s["sunrise"].tzinfo)
    return s["sunrise"] <= now <= s["sunset"]
```

### Anti-Patterns to Avoid
- **Running PyTorch model on Pi:** Always export to NCNN first. PyTorch inference is 5-6x slower on ARM.
- **Re-running NMS manually:** YOLO26 is NMS-free. Do not add a post-processing NMS step.
- **Counting on every frame:** Leads to race conditions and double-counts. Use the track-ID-registry pattern with stability timer.
- **Using cv2.imshow() on headless Pi:** The Pi runs headless. Use opencv-python-headless and log output instead of display windows.
- **Storing frame images for every detection:** Creates rapid storage growth. Deferred to DET-05 (v2).
- **Mixing diagnostic logs with egg events:** D-18 explicitly separates these. Use Python logging for diagnostics, JSONL for egg events.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Object tracking | Custom frame-to-frame matching | ByteTrack via ultralytics `model.track()` | Handles occlusion, ID assignment, lost tracks automatically |
| YOLO inference on ARM | Custom ONNX runtime setup | NCNN via `model.export(format="ncnn")` | Optimized for ARM NEON, automatic quantization |
| Sunrise/sunset times | Hardcoded time ranges or API calls | astral library | Pure Python, works offline, handles seasonal changes and latitude |
| Model training pipeline | Custom training loop | `model.train(data="data.yaml")` | Handles augmentation, scheduling, validation, early stopping |
| JSONL rotation | Custom rotation logic | Simple date-based filename pattern | `eggs-{date}.jsonl` is trivially date-rotated by filename |

**Key insight:** Ultralytics provides a batteries-included API. Detection, tracking, export, and training are all one-liners. The custom code should focus on the domain logic: zone containment, stability timing, size classification, and event logging.

## Common Pitfalls

### Pitfall 1: Forgetting `persist=True` in Tracking
**What goes wrong:** Track IDs reset every frame, so every detection gets a new ID and the same egg is counted hundreds of times.
**Why it happens:** `model.track()` without `persist=True` does not carry state between calls.
**How to avoid:** Always pass `persist=True` when processing sequential frames.
**Warning signs:** Track IDs always starting from 1 or 0 on every frame.

### Pitfall 2: NCNN Export on Wrong Platform
**What goes wrong:** Exporting NCNN model on Windows/x86 then running on Pi ARM fails or produces wrong format.
**Why it happens:** NCNN compilation is architecture-specific.
**How to avoid:** Export the model to NCNN on the Raspberry Pi itself, or use a cross-compilation workflow. The safest approach: train on GPU machine, copy .pt weights to Pi, export to NCNN on the Pi.
**Warning signs:** Model load errors mentioning architecture or SIMD instructions.

### Pitfall 3: Camera Backend Mismatch
**What goes wrong:** `cv2.VideoCapture(0)` fails on Pi because it defaults to wrong backend.
**Why it happens:** Pi 5 with Bookworm uses libcamera, not V4L2 by default. USB cameras typically work with V4L2 but may need explicit backend selection.
**How to avoid:** Use `cv2.VideoCapture(0, cv2.CAP_V4L2)` explicitly for USB cameras on Pi. Test with `camera_scanner.py` first.
**Warning signs:** Camera opens but returns black frames or `ret=False`.

### Pitfall 4: Memory Growth from Accumulating Track State
**What goes wrong:** `counted_ids` set and pending_tracks grow unboundedly over days of continuous operation.
**Why it happens:** Track IDs increment forever; old entries never cleaned up.
**How to avoid:** Periodically prune old entries. Since eggs are collected daily, clearing counted_ids when all eggs leave the zone (D-09) naturally bounds growth. Also, ByteTrack's `track_buffer` (default 30 frames) automatically drops lost tracks.
**Warning signs:** Increasing memory usage over multi-day runs.

### Pitfall 5: Insufficient Training Data
**What goes wrong:** Model detects eggs poorly in the specific nest box environment despite working on generic datasets.
**Why it happens:** Nest box lighting, angle, straw/bedding, and egg colors are unique. Generic egg datasets don't cover this.
**How to avoid:** Collect at least 100-200 images from the actual nest box at different times of day, with varying numbers of eggs. Augment with rotation, brightness, and contrast variations.
**Warning signs:** High confidence on validation set but poor real-world performance.

### Pitfall 6: Virtual Environment on Pi OS Bookworm
**What goes wrong:** `pip install` fails with externally-managed-environment error.
**Why it happens:** Raspberry Pi OS Bookworm (Python 3.11) enforces virtual environments.
**How to avoid:** Always create a venv: `python3 -m venv ~/egg-counter-venv && source ~/egg-counter-venv/bin/activate`
**Warning signs:** Error message mentioning PEP 668 or externally-managed-environment.

### Pitfall 7: Restart Re-Counting
**What goes wrong:** After camera/system restart, all visible eggs are counted again as new.
**Why it happens:** Track state (counted_ids) is lost on restart.
**How to avoid:** On startup, run detection once, count visible eggs, and add their track IDs to counted_ids immediately without logging new events (D-08). Alternatively, persist counted state to disk and reconcile.
**Warning signs:** Egg count doubles after every restart.

## Code Examples

### Custom ByteTrack Configuration
```yaml
# config/bytetrack_eggs.yaml
# Tuned for slow-moving/stationary eggs
tracker_type: bytetrack
track_high_thresh: 0.3      # Slightly higher than default for fewer false tracks
track_low_thresh: 0.1       # Keep low for occlusion recovery
new_track_thresh: 0.3       # Match high_thresh
track_buffer: 90            # 3 seconds at ~30fps -- matches stability requirement
match_thresh: 0.8           # Default IoU threshold
fuse_score: true
```

### YOLO Training Command
```python
from ultralytics import YOLO

# For single-class egg detection (bbox ratio size method)
model = YOLO("yolo26n.pt")  # Start from pretrained
results = model.train(
    data="data/dataset/data.yaml",
    epochs=100,
    imgsz=640,
    batch=16,
    device=0,  # GPU for training
    patience=20,
    save=True,
)

# For multi-class size detection (4 classes)
# Same command, but data.yaml defines 4 classes instead of 1
```

### Dataset YAML (Single Class)
```yaml
# data/dataset/data.yaml
path: ./data/dataset
train: images/train
val: images/val

names:
  0: egg
```

### Dataset YAML (Multi-Class for Size Comparison)
```yaml
# data/dataset/data_multiclass.yaml
path: ./data/dataset
train: images/train
val: images/val

names:
  0: egg-small
  1: egg-medium
  2: egg-large
  3: egg-jumbo
```

### NCNN Export on Raspberry Pi
```python
from ultralytics import YOLO

model = YOLO("best.pt")  # Trained weights
model.export(format="ncnn")
# Creates best_ncnn_model/ directory
# Use: model = YOLO("best_ncnn_model") for inference
```

### Zone Setup Tool Skeleton
```python
import cv2
import json

def setup_zone(camera_index=0, output_path="config/zone.json"):
    """Interactive tool: user draws rectangle on camera frame."""
    cap = cv2.VideoCapture(camera_index, cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    ret, frame = cap.read()
    cap.release()

    if not ret:
        print("Failed to capture frame")
        return

    roi = cv2.selectROI("Select Nest Box Zone", frame, fromCenter=False)
    cv2.destroyAllWindows()

    x, y, w, h = roi
    zone = {
        "x1": int(x), "y1": int(y),
        "x2": int(x + w), "y2": int(y + h),
        "nest_box_width_mm": 300,  # User should measure and update
        "frame_width": 1280,
        "frame_height": 720
    }

    with open(output_path, "w") as f:
        json.dump(zone, f, indent=2)
    print(f"Zone saved to {output_path}")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| YOLO11n | YOLO26n | January 2026 | ~15% faster on Pi 5, higher mAP, NMS-free architecture |
| PyTorch inference on Pi | NCNN export | 2024+ | 5-6x faster inference on ARM |
| BoT-SORT (default tracker) | ByteTrack | N/A (both available) | ByteTrack is simpler, no ReID model, better for static camera |
| Manual NMS post-processing | NMS-free (YOLO26) | January 2026 | Cleaner export, no NMS tuning needed |

**Deprecated/outdated:**
- YOLOv5/v8: Still functional but superseded by YOLO11 and YOLO26 for new projects
- PyTorch inference on Pi: Works but unacceptably slow (~525ms/frame)
- TensorRT on Pi: Not available -- NCNN is the ARM equivalent

## Open Questions

1. **YOLO26n vs YOLO11n for custom training stability**
   - What we know: YOLO26n benchmarks better on COCO. It uses MuSGD optimizer and ProgLoss.
   - What's unclear: Whether custom training with small datasets (100-200 images) converges as well with YOLO26 as YOLO11. YOLO26 is newer with less community experience.
   - Recommendation: Start with YOLO26n. If training convergence issues arise, fall back to YOLO11n. Both export to NCNN identically.

2. **Optimal frame rate for egg detection**
   - What we know: NCNN gives ~94ms/frame (~10 FPS) at 640px. Eggs are stationary.
   - What's unclear: Whether processing every frame is necessary or if 1-2 FPS is sufficient.
   - Recommendation: Process at 2-5 FPS to reduce CPU load while maintaining responsive detection. The 3-second stability timer does not require high FPS.

3. **Egg size threshold calibration**
   - What we know: USDA size standards are weight-based. Visual height is a proxy.
   - What's unclear: Exact pixel-to-mm mapping accuracy depends on camera angle, lens distortion, and egg orientation.
   - Recommendation: Start with approximate thresholds, then calibrate with actual eggs of known sizes. The comparison between bbox-ratio and multi-class approaches (D-01/D-02) will determine the better method empirically.

4. **Restart state persistence**
   - What we know: D-08 says re-detect and treat as already-counted on restart.
   - What's unclear: Whether to persist counted state to disk or rely solely on re-detection.
   - Recommendation: On startup, run detection, initialize counted_ids from detected eggs. No disk persistence needed in Phase 1 -- Phase 2 (SQLite) will handle durable state.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (standard for Python projects) |
| Config file | None -- needs Wave 0 setup |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DET-01 | YOLO model loads and returns detections on sample image | unit | `pytest tests/test_detector.py::test_model_loads -x` | Wave 0 |
| DET-02 | Same track ID is counted exactly once; stability timer works | unit | `pytest tests/test_tracker.py::test_deduplication -x` | Wave 0 |
| DET-02 | Restart re-detection does not double-count | unit | `pytest tests/test_tracker.py::test_restart_no_recount -x` | Wave 0 |
| DET-03 | Size classifier maps bbox dimensions to correct size category | unit | `pytest tests/test_size_classifier.py -x` | Wave 0 |
| DET-03 | Known egg dimensions produce correct classification | unit | `pytest tests/test_size_classifier.py::test_known_sizes -x` | Wave 0 |
| DET-04 | Event logger writes valid JSONL with required fields | unit | `pytest tests/test_logger.py::test_jsonl_output -x` | Wave 0 |
| DET-04 | Daily log rotation creates correct filenames | unit | `pytest tests/test_logger.py::test_daily_rotation -x` | Wave 0 |
| DET-02 | Zone containment check correctly filters in/out | unit | `pytest tests/test_zone.py -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `pyproject.toml` -- project metadata, pytest configuration
- [ ] `tests/conftest.py` -- shared fixtures (sample frames, mock model results, zone configs)
- [ ] `tests/test_zone.py` -- zone containment tests
- [ ] `tests/test_tracker.py` -- de-duplication, stability timer, restart logic
- [ ] `tests/test_size_classifier.py` -- size classification thresholds
- [ ] `tests/test_logger.py` -- JSONL output format, rotation
- [ ] `tests/test_detector.py` -- model loading (may need sample model or mock)
- [ ] Framework install: `pip install pytest`

## Sources

### Primary (HIGH confidence)
- [Ultralytics Tracking Docs](https://docs.ultralytics.com/modes/track/) -- ByteTrack API, persist=True, track ID access
- [Ultralytics Raspberry Pi Guide](https://docs.ultralytics.com/guides/raspberry-pi/) -- NCNN export, Pi 5 benchmarks, installation
- [Ultralytics NCNN Integration](https://docs.ultralytics.com/integrations/ncnn/) -- Export commands, ARM optimization
- [ByteTrack YAML Config](https://github.com/ultralytics/ultralytics/blob/main/ultralytics/cfg/trackers/bytetrack.yaml) -- Default parameters
- [PyPI ultralytics](https://pypi.org/project/ultralytics/) -- Version 8.4.24 confirmed
- [PyPI supervision](https://pypi.org/project/supervision/) -- Version 0.27.0 confirmed

### Secondary (MEDIUM confidence)
- [YOLO26 vs YOLO11 Comparison](https://docs.ultralytics.com/compare/yolo26-vs-yolo11/) -- NMS-free architecture, MuSGD optimizer, edge performance
- [LearnOpenCV YOLO11 on Raspberry Pi](https://learnopencv.com/yolo11-on-raspberry-pi/) -- Real-world Pi 5 performance
- [Roboflow Supervision PolygonZone](https://supervision.roboflow.com/latest/detection/tools/polygon_zone/) -- Zone-based counting
- [OpenCV Raspberry Pi Configuration](https://opencv.org/blog/configuring-raspberry-pi-for-opencv-camera-cooling/) -- Camera setup

### Tertiary (LOW confidence)
- [Raspberry Pi Forums - USB cameras](https://forums.raspberrypi.com/viewtopic.php?t=365216) -- USB camera compatibility reports (community, not official)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- ultralytics is the official, well-documented solution; versions verified on PyPI
- Architecture: HIGH -- patterns follow official ultralytics docs and community best practices
- Pitfalls: HIGH -- drawn from official docs, community forums, and documented Pi 5 deployment issues
- Size classification: MEDIUM -- the bbox-ratio approach is sound in principle but accuracy depends on camera geometry; the multi-class approach requires sufficient labeled data per size category

**Research date:** 2026-03-22
**Valid until:** 2026-04-22 (ultralytics releases frequently but API is stable)
