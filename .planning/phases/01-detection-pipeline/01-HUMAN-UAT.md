---
status: complete
phase: 01-detection-pipeline
source: [01-VERIFICATION.md]
started: 2026-03-23T00:00:00Z
updated: 2026-03-23T16:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Daylight Pause Behavior
expected: With camera and model, running `egg-counter run --model <path>` during nighttime prints "Waiting for daylight..." and pauses
result: pass

### 2. Zone Setup Tool Interactive Flow
expected: Running `python tools/setup_zone.py` with camera opens frame, user draws rectangle, config/zone.json is written
result: pass

### 3. End-to-End Detection on Pi
expected: Running `egg-counter run --model <yolo11n-egg.pt> --camera 0` with eggs in nest box prints "New egg #1 -- large" after 3s stability and writes JSONL to logs/
result: pass
note: Previously reported "No visual verification tools" — gap closed by plan 01-04

### 4. Live GUI Preview with Camera
expected: Running `egg-counter preview --model <path> --camera 0` opens an OpenCV window showing live camera feed with bounding boxes, size labels, confidence scores, zone rectangle, and egg count overlay
result: pass

### 5. Preview Video Playback Mode
expected: Running `egg-counter preview --model <path> --video <file>` plays back video with detection overlays at correct frame rate, exits cleanly on 'q' or ESC
result: issue
reported: "I should be also be able to setup zone for videos"
severity: major

## Summary

total: 5
passed: 4
issues: 1
pending: 0
skipped: 0
blocked: 0

## Gaps

- truth: "User can visually verify detection is working via live GUI feed"
  status: resolved
  reason: "Plan 01-04 implemented preview.py with draw_detections and run_preview; CLI preview subcommand added"
  severity: major
  test: 3
  root_cause: ""
  artifacts: [src/egg_counter/preview.py, tests/test_preview.py]
  missing: []
  debug_session: ""

- truth: "Zone setup tool supports video file input in addition to live camera"
  status: failed
  reason: "User reported: I should be also be able to setup zone for videos"
  severity: major
  test: 5
  root_cause: ""
  artifacts: []
  missing:
    - "tools/setup_zone.py accepts --video <file> flag to load a frame from video instead of camera"
  debug_session: ""
