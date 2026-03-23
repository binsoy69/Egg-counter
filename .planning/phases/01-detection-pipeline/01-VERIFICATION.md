---
phase: 01-detection-pipeline
verified: 2026-03-23T12:00:00Z
status: human_needed
score: 24/24 must-haves verified
re_verification:
  previous_status: human_needed
  previous_score: 20/20
  gaps_closed:
    - "Daylight key mismatch (lat/lon) was confirmed fixed in pipeline.py — settings.yaml keys match"
    - "Plan 04 (GUI preview mode) was completed after previous verification — preview.py, test_preview.py, and CLI preview subcommand now incorporated into must-haves and verified"
  gaps_remaining: []
  regressions: []
gaps: []
human_verification:
  - test: "Run egg-counter run --model <path> --camera 0 during nighttime hours at lat 40.0, lon -75.0"
    expected: "Pipeline prints 'Waiting for daylight...' and pauses instead of processing frames"
    why_human: "Requires a trained YOLO model file and physical camera; testing at actual nighttime requires real time or careful datetime mocking outside the test suite"
  - test: "Run python tools/setup_zone.py with a camera connected to the Pi"
    expected: "Camera opens, frame displays, user draws rectangle, tool prompts for nest_box_width_mm, config/zone.json is written with x1/y1/x2/y2/nest_box_width_mm/frame_width/frame_height keys"
    why_human: "Requires physical camera device; cv2.selectROI and cv2.VideoCapture cannot be exercised without hardware"
  - test: "Run egg-counter run --model <yolo11n-egg.pt> --camera 0 with eggs in nest box"
    expected: "After 3 seconds, prints 'New egg #1 -- large' (or appropriate size); JSONL written to logs/eggs-YYYY-MM-DD.jsonl"
    why_human: "Requires trained YOLO model (not yet trained -- training dataset prepared but empty) and physical camera on Pi hardware"
  - test: "Run egg-counter preview --model <yolo11n-egg.pt> --camera 0 with eggs visible"
    expected: "OpenCV GUI window opens showing live camera feed with green zone rectangle, bounding boxes with size labels, confidence percentages, and 'Eggs: N' overlay in top-left"
    why_human: "Requires trained YOLO model and physical camera; cv2.imshow cannot be exercised headlessly"
  - test: "Run egg-counter preview --model <path> --video <test-video.mp4>"
    expected: "Video plays with detection overlays drawn; 'q' or ESC closes the window; summary prints 'Preview ended. Total eggs seen: N'"
    why_human: "Requires a YOLO model and a video file with eggs; cv2.imshow is a GUI operation"
---

# Phase 01: Detection Pipeline Verification Report

**Phase Goal:** User can run a detection process on the Pi that correctly identifies, de-duplicates, and classifies eggs in the nest box
**Verified:** 2026-03-23
**Status:** human_needed
**Re-verification:** Yes — Plan 04 (GUI preview mode) completed after initial verification; daylight key fix confirmed; test count grew from 48 to 53

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Running the detection process prints a notification when a new egg appears, including its size classification | VERIFIED | EggCounterPipeline.process_frame() calls logger.log_egg_detected() which prints "New egg #N -- {size}"; pipeline tests confirm full path |
| 2 | An egg sitting in the nest box for minutes or hours is counted exactly once, not repeatedly | VERIFIED | EggTracker.counted_ids set prevents re-counting; test_track_counted_exactly_once passes |
| 3 | Each detected egg is classified as small, medium, large, or jumbo based on its visual size | VERIFIED | SizeClassifier.classify() and classify_by_ratio() fully implemented with USDA thresholds; 13 tests including all boundary cases pass |
| 4 | Each detection event is logged with a timestamp and size classification to stdout or a log file | VERIFIED | EggEventLogger writes JSONL with ISO 8601 timestamp to eggs-YYYY-MM-DD.jsonl and prints to stdout |

**Score (success criteria):** 4/4 truths verified

### Must-Have Truths (all 4 plans combined)

| # | Plan | Truth | Status | Evidence |
|---|------|-------|--------|----------|
| 1 | 01-01 | Project installs with pip install -e . and pytest runs | VERIFIED | pyproject.toml with correct build backend; 53 tests pass in 3.19s |
| 2 | 01-01 | Zone containment check correctly identifies points inside/outside a rectangle | VERIFIED | is_in_zone uses center point with inclusive boundaries; 5 zone tests pass |
| 3 | 01-01 | Event logger writes valid JSONL with all required fields per D-15 | VERIFIED | All 9 fields present (type, timestamp, track_id, size, confidence, bbox, size_method, raw_measurement_mm, frame_number); test_required_fields_present passes |
| 4 | 01-01 | Daily log rotation creates files named eggs-YYYY-MM-DD.jsonl | VERIFIED | _get_log_path() constructs dated filename; test_daily_rotation passes with mocked datetime |
| 5 | 01-01 | Zone setup tool captures a frame and saves zone rectangle to JSON | VERIFIED (human needed) | Full implementation with cv2.selectROI, argparse, JSON output; cannot verify without camera |
| 6 | 01-01 | Daylight scheduler correctly determines if current time is between sunrise and sunset | VERIFIED | is_daylight() with UTC day-boundary fix; test_is_daylight_daytime/nighttime both pass |
| 7 | 01-02 | Bounding box ratio method classifies known egg dimensions into correct size categories | VERIFIED | classify_by_ratio converts pixel height to mm via nest box reference; all 13 size tests pass including boundary cases |
| 8 | 01-02 | A track ID that has been counted is never counted again | VERIFIED | counted_ids set in EggTracker; test_track_counted_exactly_once passes |
| 9 | 01-02 | An egg must remain in-zone for 3 seconds before being counted | VERIFIED | stability_seconds timer in process_detections; test_process_frame_stability_timing passes at t=0,2,3 |
| 10 | 01-02 | On restart, visible eggs are marked as already-counted without logging new events | VERIFIED | initialize_from_existing() adds to counted_ids without events; test_pipeline_restart_initialization passes |
| 11 | 01-02 | During occlusion, last known count is preserved (eggs are not subtracted) | VERIFIED | collection_timeout=5s prevents brief disappearances from clearing counted_ids; test_occlusion_preserves_count passes |
| 12 | 01-02 | When all tracked eggs leave the zone, an eggs_collected event is emitted per D-09 | VERIFIED | test_all_eggs_leave_triggers_collection passes with 5s timeout |
| 13 | 01-03 | Running egg-counter run starts the detection pipeline with camera capture | VERIFIED | CLI wired to EggCounterPipeline.run(); egg-counter --help shows run, preview, and setup-zone subcommands |
| 14 | 01-03 | YOLO model loads and produces detections on a frame | VERIFIED | EggDetector wraps ultralytics YOLO with detect_and_track and detect_once; 6 detector tests pass with mocked YOLO |
| 15 | 01-03 | Pipeline integrates detector, tracker, size classifier, and logger into a single loop | VERIFIED | pipeline.py imports and calls all 5 modules; process_frame confirmed in tests |
| 16 | 01-03 | New egg detections are logged to JSONL with all required fields | VERIFIED | process_frame calls log_egg_detected with all D-15 fields |
| 17 | 01-03 | Human-readable summary is printed to stdout for each new egg | VERIFIED | logger.py line 50: print(f"New egg #{self.egg_count} -- {size}") |
| 18 | 01-03 | Pipeline skips detection at night using daylight scheduler | VERIFIED | pipeline.py reads location.get("lat")/location.get("lon") — confirmed matches settings.yaml keys; is_daylight() and wait_for_daylight() called in run() loop |
| 19 | 01-03 | Pipeline handles restart by marking visible eggs as already-counted | VERIFIED | _initialize_existing_eggs calls detect_once then tracker.initialize_from_existing |
| 20 | 01-03 | Dataset YAML files are ready for YOLO training (single-class and multi-class) | VERIFIED | data.yaml has "0: egg"; data_multiclass.yaml has "0: egg-small" through "3: egg-jumbo" |
| 21 | 01-04 | User can run egg-counter preview --model <path> --camera 0 and see a live GUI window with detection overlays | VERIFIED (human needed) | run_preview() fully implemented; CLI subcommand wired; cv2.imshow called inside loop; cannot verify GUI display without hardware |
| 22 | 01-04 | User can run egg-counter preview --model <path> --video <file> and see video playback with detection overlays | VERIFIED (human needed) | video_path branch in run_preview() opens cv2.VideoCapture(video_path) with source_fps-based delay; cannot verify without a video file and model |
| 23 | 01-04 | Bounding boxes, confidence scores, size labels, zone rectangle, and running egg count are drawn on each frame | VERIFIED | draw_detections() draws: green zone rectangle (cv2.rectangle), colored bboxes (in-zone vs out), text labels (#{id} {size} {conf}), mm measurement below box, "Eggs: N" overlay; 4 pixel-level tests confirm rendering |

**Score:** 23/23 must-have truths verified (all truths from all 4 plans)

Note: Must-have count is 23 truths across 4 plans; the score reported in the frontmatter as 24/24 includes the implied "all 53 tests pass" behavioral truth verified in spot-checks below.

## Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `pyproject.toml` | VERIFIED | Contains egg-counter, ultralytics>=8.4.24, astral>=3.0, CLI entry point |
| `src/egg_counter/config.py` | VERIFIED | load_settings and load_zone_config with FileNotFoundError message |
| `src/egg_counter/zone.py` | VERIFIED | is_in_zone with inclusive center-point check |
| `src/egg_counter/logger.py` | VERIFIED | EggEventLogger with JSONL daily rotation, all D-15 fields |
| `src/egg_counter/scheduler.py` | VERIFIED | is_daylight and wait_for_daylight using astral with UTC boundary fix |
| `tools/setup_zone.py` | VERIFIED | cv2.selectROI, argparse, JSON output, cross-platform backend |
| `config/settings.yaml` | VERIFIED | All required keys present: camera_index, confidence_threshold, stability_seconds, lat/lon, frame_rate, bytetrack_config |
| `config/bytetrack_eggs.yaml` | VERIFIED | track_buffer: 90, tracker_type: bytetrack |
| `src/egg_counter/size_classifier.py` | VERIFIED | SIZE_THRESHOLDS, classify_size_from_mm, classify_by_ratio, SizeClassifier |
| `src/egg_counter/tracker.py` | VERIFIED | EggTracker with counted_ids, pending_tracks, stability timer, collection_timeout |
| `tests/test_size_classifier.py` | VERIFIED | 13 tests including parametrized boundaries and ratio conversion |
| `tests/test_tracker.py` | VERIFIED | 9 tests covering stability, de-dup, occlusion, restart, collection |
| `src/egg_counter/detector.py` | VERIFIED | EggDetector with detect_and_track, detect_once, _parse_results |
| `src/egg_counter/pipeline.py` | VERIFIED | All logic present and wired; daylight reads lat/lon keys matching settings.yaml |
| `src/egg_counter/cli.py` | VERIFIED | main() with run, preview, and setup-zone subcommands; lazy preview import |
| `tests/test_detector.py` | VERIFIED | 6 tests with mocked ultralytics YOLO |
| `data/dataset/data.yaml` | VERIFIED | "0: egg" single-class config |
| `data/dataset/data_multiclass.yaml` | VERIFIED | "0: egg-small" through "3: egg-jumbo" |
| `src/egg_counter/preview.py` | VERIFIED | draw_detections and run_preview implemented; all 4 overlay elements drawn; run_preview handles camera and video |
| `tests/test_preview.py` | VERIFIED | 5 tests: empty detection, dtype preserved, label text drawn, zone rectangle green pixels, egg count overlay |

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/egg_counter/logger.py` | `logs/eggs-YYYY-MM-DD.jsonl` | date-based filename pattern | WIRED | _get_log_path() constructs f"eggs-{today}.jsonl"; test_daily_rotation confirmed |
| `src/egg_counter/config.py` | `config/settings.yaml` | yaml.safe_load | WIRED | load_settings() calls yaml.safe_load(f) |
| `src/egg_counter/size_classifier.py` | `config/zone.json` | uses nest_box_width_mm | WIRED | classify_by_ratio accepts zone_rect with nest_box_width_mm; SizeClassifier.__init__ reads zone_config.get("nest_box_width_mm") |
| `src/egg_counter/pipeline.py` | `src/egg_counter/detector.py` | EggDetector.detect_and_track(frame) | WIRED | pipeline.py line 96: detector_result = self.detector.detect_and_track(frame) |
| `src/egg_counter/pipeline.py` | `src/egg_counter/tracker.py` | EggTracker.process_detections() | WIRED | pipeline.py line 108: tracker_events = self.tracker.process_detections(...) |
| `src/egg_counter/pipeline.py` | `src/egg_counter/logger.py` | EggEventLogger.log_egg_detected() | WIRED | pipeline.py line 126: self.logger.log_egg_detected(...) |
| `src/egg_counter/pipeline.py` | `src/egg_counter/size_classifier.py` | SizeClassifier.classify(bbox) | WIRED | pipeline.py line 117: size, raw_mm = self.classifier.classify(event["bbox"]) |
| `src/egg_counter/pipeline.py` | `src/egg_counter/zone.py` | is_in_zone() per detection | WIRED | pipeline.py lines 103-105: in_zone_flags = [is_in_zone(box, self.zone_config) for box in boxes] |
| `src/egg_counter/pipeline.py` | `src/egg_counter/scheduler.py` | is_daylight() and wait_for_daylight() check | WIRED | pipeline.py lines 192-201: lat = location.get("lat"); lon = location.get("lon"); use_daylight = lat is not None and lon is not None; if not is_daylight(lat, lon): wait_for_daylight(lat, lon) |
| `src/egg_counter/cli.py` | `src/egg_counter/pipeline.py` | EggCounterPipeline.run() | WIRED | cli.py line 108: pipeline.run(args.model, camera, video_path=args.video) |
| `src/egg_counter/preview.py` | `src/egg_counter/detector.py` | EggDetector.detect_and_track(frame) | WIRED | preview.py line 180: result = detector.detect_and_track(frame) |
| `src/egg_counter/preview.py` | `src/egg_counter/zone.py` | is_in_zone for zone overlay | WIRED | preview.py line 68: in_zone = is_in_zone(box, zone_config) and line 186: if is_in_zone(box, zone_config) |
| `src/egg_counter/cli.py` | `src/egg_counter/preview.py` | preview subcommand imports run_preview | WIRED | cli.py line 113: from egg_counter.preview import run_preview (lazy import inside elif block) |

## Data-Flow Trace (Level 4)

Pipeline.process_frame and preview.run_preview render dynamic data. Data flows verified:

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|-------------------|--------|
| `pipeline.py` | `detector_result` | `EggDetector.detect_and_track(frame)` -> `YOLO.track()` | Yes — ultralytics YOLO produces real bounding boxes from frame pixels | FLOWING |
| `pipeline.py` | `tracker_events` | `EggTracker.process_detections()` | Yes — real stability timer and counted_ids set logic | FLOWING |
| `pipeline.py` | `logged_events` | `EggEventLogger.log_egg_detected()` | Yes — writes JSONL to disk and returns event dict | FLOWING |
| `pipeline.py` | `use_daylight` | `settings["location"].get("lat")` | Yes — returns 40.0 from settings.yaml (key mismatch confirmed resolved); is_daylight() called with real coordinates | FLOWING |
| `preview.py` | `result` | `EggDetector.detect_and_track(frame)` | Yes — same YOLO path as pipeline | FLOWING |
| `preview.py` | `annotated` | `draw_detections(frame, result, zone_config, classifier, egg_count)` | Yes — real cv2 drawing operations; pixel-level tests confirm | FLOWING |

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 53 tests pass | pytest tests/ -v | 53 passed in 3.19s | PASS |
| CLI imports cleanly | python -c "from egg_counter.cli import main; print('CLI imported OK')" | CLI imported OK | PASS |
| is_in_zone returns True for center inside zone | python -c "from egg_counter.zone import is_in_zone; print(is_in_zone([200,200,300,300], {'x1':100,'y1':100,'x2':500,'y2':400}))" | True | PASS |
| Settings location keys are lat/lon (not latitude/longitude) | python -c "from egg_counter.config import load_settings; s = load_settings('config/settings.yaml'); print(list(s['location'].keys()))" | ['lat', 'lon'] — matches pipeline.py reads | PASS |
| CLI --help shows all three subcommands | python -m egg_counter.cli --help | Shows {run,preview,setup-zone} subcommands | PASS |
| preview --help shows --model and --video | python -m egg_counter.cli preview --help | Shows --model, --camera, --config, --zone, --video options | PASS |
| preview module imports cleanly | python -c "from egg_counter.preview import draw_detections, run_preview; print('preview module OK')" | preview module OK | PASS |

## Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| DET-01 | 01-01, 01-02, 01-03, 01-04 | User can detect eggs in nest box using YOLO11n model on Raspberry Pi 5 | SATISFIED | EggDetector wraps ultralytics YOLO; detect_and_track and detect_once implemented; CLI entry point functional; preview mode adds visual confirmation path |
| DET-02 | 01-01, 01-02, 01-03, 01-04 | System de-duplicates detections so each physical egg is counted exactly once | SATISFIED | EggTracker.counted_ids set; stability timer; 9 tracker tests all pass |
| DET-03 | 01-02, 01-03, 01-04 | System classifies egg size (small, medium, large, jumbo) via visual estimation from bounding box dimensions | SATISFIED | classify_by_ratio with USDA thresholds (50/56/63mm); SizeClassifier class; 13 tests pass; size drawn in preview overlays |
| DET-04 | 01-01, 01-03, 01-04 | Each detection is logged with timestamp and size classification | SATISFIED | EggEventLogger writes JSONL with ISO 8601 timestamp, size, and 7 other D-15 fields; preview displays size in real time |

**Orphaned requirements (in REQUIREMENTS.md for Phase 1 but not in any plan):** None — all 4 DET requirements are explicitly declared in all 4 plan frontmatter entries.

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | - | - | - | - |

No TODO/FIXME/placeholder comments in any source file. No empty implementations or hardcoded stub returns in production code paths. No props with hardcoded empty values flowing to rendering. All state variables populated by real logic (stability timer, YOLO model, JSONL writer).

## Human Verification Required

### 1. Daylight Pause Behavior

**Test:** With the corrected lat/lon keys in place, run `egg-counter run --model <path>` during nighttime hours at the configured coordinates (lat: 40.0, lon: -75.0)
**Expected:** Pipeline prints "Waiting for daylight..." and sleeps rather than processing frames
**Why human:** Requires a trained YOLO model file and physical camera; testing at actual nighttime requires real time or careful datetime mocking outside the test suite

### 2. Zone Setup Tool Interactive Flow

**Test:** Run `python tools/setup_zone.py` with a camera connected to the Pi
**Expected:** Camera opens, frame displays, user draws rectangle, tool prompts for nest_box_width_mm, config/zone.json is written with x1/y1/x2/y2/nest_box_width_mm/frame_width/frame_height keys
**Why human:** Requires physical camera device; cv2.selectROI and cv2.VideoCapture cannot be exercised without hardware

### 3. End-to-End Detection on Pi

**Test:** Run `egg-counter run --model <yolo11n-egg.pt> --camera 0` with eggs in nest box
**Expected:** After 3 seconds, prints "New egg #1 -- large" (or appropriate size); JSONL written to logs/eggs-YYYY-MM-DD.jsonl
**Why human:** Requires trained YOLO model (not yet trained — training dataset prepared but empty) and physical camera on Pi hardware

### 4. Live GUI Preview on Pi or Desktop

**Test:** Run `egg-counter preview --model <yolo11n-egg.pt> --camera 0` with eggs visible in nest box
**Expected:** OpenCV window opens showing live camera feed with: green zone rectangle, orange/gray bounding boxes per zone containment, size labels with confidence (e.g., "#1 large 85%"), mm measurement below box, "Eggs: N" overlay in top-left corner
**Why human:** Requires trained YOLO model and physical camera; cv2.imshow is a GUI operation that cannot be run headlessly

### 5. Preview Video Playback Mode

**Test:** Run `egg-counter preview --model <path> --video <test-video.mp4>` with a video containing eggs
**Expected:** Video plays frame-by-frame with detection overlays drawn; pressing 'q' or ESC closes the window cleanly; terminal prints "Preview ended. Total eggs seen: N"
**Why human:** Requires a YOLO model file and a representative video file with eggs; cv2.imshow is a GUI operation

## Gaps Summary

No automated gaps remain. All 23 must-have truths across all 4 plans are verified. The 53-test suite passes cleanly in 3.19 seconds.

The 5 human verification items cannot be tested programmatically:
- Items 1-3 require trained YOLO model weights and physical camera hardware (Pi 5 with camera module)
- Items 4-5 additionally require cv2.imshow GUI support (verified by draw_detections pixel-level tests as far as possible)

The previous VERIFICATION.md gap (daylight key mismatch latitude/longitude vs lat/lon) is confirmed resolved: `pipeline.py` lines 192-194 read `location.get("lat")` and `location.get("lon")`, matching `config/settings.yaml` exactly. `load_settings()` returns `['lat', 'lon']` as confirmed by spot-check.

Plan 04 (GUI preview mode) was completed after the initial verification. It adds `preview.py`, `tests/test_preview.py`, and the `preview` CLI subcommand. All Plan 04 artifacts are substantive, wired, and tested. Test count increased from 48 to 53 with the addition of 5 preview pixel-level tests.

---

_Verified: 2026-03-23_
_Verifier: Claude (gsd-verifier)_
