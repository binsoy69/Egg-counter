---
phase: 01-detection-pipeline
plan: 02
subsystem: detection
tags: [yolo, egg-size, tracking, bytetrack, tdd, python]

# Dependency graph
requires: []
provides:
  - "Size classifier: classify_by_ratio, classify_size_from_mm, SizeClassifier"
  - "Egg tracker: EggTracker with de-duplication, stability timer, restart handling"
affects: [01-detection-pipeline plan 03 pipeline integration]

# Tech tracking
tech-stack:
  added: [pytest]
  patterns: [TDD red-green, pure-logic modules with no I/O deps, deterministic timestamp testing]

key-files:
  created:
    - src/egg_counter/size_classifier.py
    - src/egg_counter/tracker.py
    - tests/test_size_classifier.py
    - tests/test_tracker.py
  modified:
    - .gitignore

key-decisions:
  - "Added collection_timeout parameter (5s default) to distinguish occlusion from collection events"
  - "Size thresholds use strict greater-than (>63mm jumbo, >56mm large, >50mm medium, <=50mm small)"
  - "Deterministic timestamp-based testing -- no time.time() in tests"

patterns-established:
  - "TDD workflow: failing test commit, then implementation commit"
  - "Pure domain modules: no file I/O or external deps, receive data as parameters"
  - "Event-based tracker API: process_detections returns list of event dicts"

requirements-completed: [DET-02, DET-03]

# Metrics
duration: 5min
completed: 2026-03-23
---

# Phase 1 Plan 02: Size Classifier and Tracker Summary

**Bbox-ratio size classifier (50/56/63mm USDA thresholds) and EggTracker with 3s stability timer, de-duplication, occlusion handling, restart safety, and collection detection**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-22T22:08:47Z
- **Completed:** 2026-03-22T22:13:34Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Size classifier maps bounding box pixel height to mm using nest box reference width, then to small/medium/large/jumbo
- Egg tracker ensures each track ID counted exactly once after 3-second stability period
- Occlusion handling preserves count during brief disappearances (collection_timeout prevents false collection)
- Restart initialization marks existing eggs as counted without emitting events
- Collection event emitted when all eggs leave zone for longer than collection_timeout
- 22 total tests pass (13 size classifier + 9 tracker)

## Task Commits

Each task was committed atomically:

1. **Task 1: Size classifier (RED)** - `07cc483` (test)
2. **Task 1: Size classifier (GREEN)** - `d019e90` (feat)
3. **Task 2: Egg tracker (RED)** - `02b9940` (test)
4. **Task 2: Egg tracker (GREEN)** - `952c21e` (feat)
5. **Gitignore update** - `9704eb6` (chore)

_TDD tasks each have test + implementation commits._

## Files Created/Modified
- `src/egg_counter/size_classifier.py` - SIZE_THRESHOLDS, classify_size_from_mm, classify_by_ratio, SizeClassifier class
- `src/egg_counter/tracker.py` - EggTracker with counted_ids, pending_tracks, stability timer, collection detection
- `tests/test_size_classifier.py` - 13 tests: basic sizes, boundaries, ratio conversion, class wrapper
- `tests/test_tracker.py` - 9 tests: stability, de-duplication, occlusion, restart, collection
- `src/__init__.py` - Package init
- `src/egg_counter/__init__.py` - Package init
- `tests/__init__.py` - Package init
- `.gitignore` - Added __pycache__/, *.pyc, .pytest_cache/

## Decisions Made
- Added `collection_timeout` parameter (default 5s) to EggTracker to distinguish brief occlusion (hen sitting) from actual egg collection. Without this, a single frame with no detections would falsely trigger collection, clearing counted eggs.
- Size thresholds use strict greater-than comparisons: >63mm is jumbo, >56mm is large, >50mm is medium, <=50mm is small.
- Tests use explicit timestamps (0.0, 1.0, 3.0, etc.) instead of time.time() for deterministic behavior.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed occlusion vs collection conflict**
- **Found during:** Task 2 (Tracker implementation)
- **Issue:** Plan spec for collection detection (`len(track_ids) == 0`) also triggers during occlusion (hen sitting on egg). A single empty-detection frame would clear counted_ids, losing the egg count.
- **Fix:** Added `collection_timeout` parameter with timestamp-based detection. Collection only fires if no detections seen for >= collection_timeout seconds after last detection. Brief occlusion gaps (< 5s) are preserved.
- **Files modified:** src/egg_counter/tracker.py, tests/test_tracker.py
- **Verification:** Both occlusion and collection tests pass -- occlusion at 2s gap preserves count, collection at 5s+ gap emits event.
- **Committed in:** 952c21e (Task 2 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Essential fix -- without collection_timeout, occlusion would incorrectly reset egg count. No scope creep.

## Issues Encountered
None beyond the occlusion/collection conflict documented above.

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - both modules are fully implemented with complete logic.

## Next Phase Readiness
- Size classifier and tracker are pure-logic modules ready for pipeline integration in Plan 03
- Both export clean interfaces: `classify_by_ratio`/`SizeClassifier` and `EggTracker`
- Tracker accepts parallel lists (track_ids, boxes, in_zone_flags, timestamp) matching ByteTrack output format

## Self-Check: PASSED

- All 4 source/test files exist on disk
- All 5 commit hashes found in git log

---
*Phase: 01-detection-pipeline*
*Completed: 2026-03-23*
