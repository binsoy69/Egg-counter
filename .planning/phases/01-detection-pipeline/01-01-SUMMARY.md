---
phase: 01-detection-pipeline
plan: 01
subsystem: detection
tags: [python, yolo, ultralytics, astral, pyyaml, opencv, bytetrack, jsonl]

# Dependency graph
requires: []
provides:
  - "Installable Python package (egg-counter) with pip install -e ."
  - "Config system loading settings.yaml and zone.json"
  - "Zone containment check (is_in_zone)"
  - "JSONL event logger with daily rotation (EggEventLogger)"
  - "Daylight scheduler using astral (is_daylight)"
  - "Interactive zone setup tool (tools/setup_zone.py)"
  - "ByteTrack tracker config tuned for stationary eggs"
affects: [01-detection-pipeline plan 02, 01-detection-pipeline plan 03]

# Tech tracking
tech-stack:
  added: [ultralytics, opencv-python-headless, numpy, astral, pyyaml, pytest]
  patterns: [src-layout package, YAML config, JSONL logging, TDD]

key-files:
  created:
    - pyproject.toml
    - src/egg_counter/__init__.py
    - src/egg_counter/config.py
    - src/egg_counter/zone.py
    - src/egg_counter/logger.py
    - src/egg_counter/scheduler.py
    - config/settings.yaml
    - config/bytetrack_eggs.yaml
    - tools/setup_zone.py
    - tests/conftest.py
    - tests/test_zone.py
    - tests/test_logger.py
  modified:
    - .gitignore

key-decisions:
  - "Used src-layout for Python package structure (standard, avoids import confusion)"
  - "Used _utcnow() helper in scheduler for testable datetime mocking without breaking astral"
  - "Added UTC day-boundary handling in is_daylight for western-hemisphere locations"

patterns-established:
  - "TDD: write failing tests first, then implement, commit separately"
  - "Config: YAML for settings, JSON for zone, loaded via config.py"
  - "Logging: JSONL daily rotation with eggs-YYYY-MM-DD.jsonl naming"
  - "Zone: dict-based zone_rect with x1/y1/x2/y2 keys, inclusive boundaries"

requirements-completed: [DET-04, DET-02]

# Metrics
duration: 9min
completed: 2026-03-23
---

# Phase 01 Plan 01: Project Foundation Summary

**Python package with config system, zone containment, JSONL event logger with daily rotation, astral daylight scheduler, and interactive zone setup tool -- all TDD with 16 passing tests**

## Performance

- **Duration:** 9 min
- **Started:** 2026-03-22T22:08:13Z
- **Completed:** 2026-03-22T22:17:00Z
- **Tasks:** 2
- **Files modified:** 13

## Accomplishments
- Installable Python package with all dependencies (ultralytics, opencv, astral, etc.)
- Config system loading YAML settings and JSON zone config with helpful error messages
- Zone containment check using bbox center with inclusive boundaries
- JSONL event logger with daily file rotation, stdout summaries, and all D-15 required fields
- Daylight scheduler with UTC day-boundary handling for western-hemisphere locations
- Interactive zone setup tool using cv2.selectROI with cross-platform camera backends

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Project scaffolding tests** - `ff3a2d9` (test)
2. **Task 1 GREEN: Config and zone modules** - `60fe286` (feat)
3. **Task 2 RED: Logger and scheduler tests** - `ae33910` (test)
4. **Task 2 GREEN: Logger, scheduler, zone tool** - `97a12dd` (feat)
5. **Gitignore cleanup** - `ac2e1a4` (chore)

## Files Created/Modified
- `pyproject.toml` - Project metadata, dependencies, pytest config
- `src/egg_counter/__init__.py` - Package init with version
- `src/egg_counter/config.py` - load_settings and load_zone_config functions
- `src/egg_counter/zone.py` - is_in_zone bbox center containment check
- `src/egg_counter/logger.py` - EggEventLogger with JSONL daily rotation
- `src/egg_counter/scheduler.py` - is_daylight and wait_for_daylight using astral
- `config/settings.yaml` - Default settings (camera, confidence, location)
- `config/bytetrack_eggs.yaml` - ByteTrack config tuned for stationary eggs
- `tools/setup_zone.py` - Interactive zone configuration via cv2.selectROI
- `tests/conftest.py` - Shared fixtures (zone, bbox, temp dirs)
- `tests/test_zone.py` - 8 tests for zone and config modules
- `tests/test_logger.py` - 8 tests for logger and scheduler modules
- `.gitignore` - Updated for Python artifacts

## Decisions Made
- Used src-layout for Python package (standard best practice, avoids import ambiguity)
- Extracted `_utcnow()` helper in scheduler for clean datetime mocking without breaking astral internals
- Added UTC day-boundary correction in `is_daylight` -- astral returns sunset before sunrise for western hemisphere locations, so we check today+yesterday with day wrapping

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed astral sunset/sunrise UTC day-boundary issue**
- **Found during:** Task 2 (scheduler implementation)
- **Issue:** astral returns sunset time earlier than sunrise for locations with negative UTC offsets (e.g., lon=-75), making a simple sunrise<=now<=sunset comparison fail for daytime hours
- **Fix:** Added day-boundary correction: check both today and yesterday's sun windows, and push sunset forward by 1 day when it's earlier than sunrise
- **Files modified:** src/egg_counter/scheduler.py
- **Verification:** Both daylight tests pass (noon=True, midnight=False)
- **Committed in:** 97a12dd (Task 2 commit)

**2. [Rule 1 - Bug] Fixed pyproject.toml build backend**
- **Found during:** Task 1 (pip install)
- **Issue:** Used incorrect build backend `setuptools.backends._legacy:_Backend`
- **Fix:** Changed to standard `setuptools.build_meta`
- **Files modified:** pyproject.toml
- **Verification:** pip install -e ".[dev]" succeeds
- **Committed in:** 60fe286 (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Issues Encountered
None beyond the auto-fixed deviations above.

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all modules are fully functional with real implementations.

## Next Phase Readiness
- Package installs cleanly, all 16 tests pass
- Config, zone, logger, and scheduler modules ready for Plan 02 (domain logic)
- Plan 02 can import from egg_counter.config, egg_counter.zone, egg_counter.logger, egg_counter.scheduler
- Zone setup tool ready for one-time calibration when camera is positioned

## Self-Check: PASSED

All 13 files verified present. All 5 commit hashes verified in git log.

---
*Phase: 01-detection-pipeline*
*Completed: 2026-03-23*
