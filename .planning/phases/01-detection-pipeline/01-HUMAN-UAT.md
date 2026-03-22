---
status: partial
phase: 01-detection-pipeline
source: [01-VERIFICATION.md]
started: 2026-03-23T00:00:00Z
updated: 2026-03-23T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Daylight Pause Behavior
expected: With camera and model, running `egg-counter run --model <path>` during nighttime prints "Waiting for daylight..." and pauses
result: [pending]

### 2. Zone Setup Tool Interactive Flow
expected: Running `python tools/setup_zone.py` with camera opens frame, user draws rectangle, config/zone.json is written
result: [pending]

### 3. End-to-End Detection on Pi
expected: Running `egg-counter run --model <yolo11n-egg.pt> --camera 0` with eggs in nest box prints "New egg #1 -- large" after 3s stability and writes JSONL to logs/
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
