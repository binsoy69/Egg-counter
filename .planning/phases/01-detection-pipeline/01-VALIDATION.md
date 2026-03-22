---
phase: 1
slug: detection-pipeline
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-22
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | None — Wave 0 installs |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 0 | DET-01 | unit | `pytest tests/test_detector.py::test_model_loads -x` | ❌ W0 | ⬜ pending |
| 01-02-01 | 02 | 1 | DET-02 | unit | `pytest tests/test_zone.py -x` | ❌ W0 | ⬜ pending |
| 01-02-02 | 02 | 1 | DET-02 | unit | `pytest tests/test_tracker.py::test_deduplication -x` | ❌ W0 | ⬜ pending |
| 01-02-03 | 02 | 1 | DET-02 | unit | `pytest tests/test_tracker.py::test_restart_no_recount -x` | ❌ W0 | ⬜ pending |
| 01-03-01 | 03 | 1 | DET-03 | unit | `pytest tests/test_size_classifier.py -x` | ❌ W0 | ⬜ pending |
| 01-03-02 | 03 | 1 | DET-03 | unit | `pytest tests/test_size_classifier.py::test_known_sizes -x` | ❌ W0 | ⬜ pending |
| 01-04-01 | 04 | 1 | DET-04 | unit | `pytest tests/test_logger.py::test_jsonl_output -x` | ❌ W0 | ⬜ pending |
| 01-04-02 | 04 | 1 | DET-04 | unit | `pytest tests/test_logger.py::test_daily_rotation -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `pyproject.toml` — project metadata, pytest configuration
- [ ] `tests/conftest.py` — shared fixtures (sample frames, mock model results, zone configs)
- [ ] `tests/test_zone.py` — zone containment tests
- [ ] `tests/test_tracker.py` — de-duplication, stability timer, restart logic
- [ ] `tests/test_size_classifier.py` — size classification thresholds
- [ ] `tests/test_logger.py` — JSONL output format, rotation
- [ ] `tests/test_detector.py` — model loading (may need sample model or mock)
- [ ] Framework install: `pip install pytest`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Camera captures live frames from USB camera | DET-01 | Requires physical hardware | Point USB camera at nest box, run detection process, verify frames are captured |
| End-to-end egg detection on live feed | DET-01 | Requires real eggs and camera | Place eggs in nest box, run pipeline, verify detections appear |
| Size classification accuracy with real eggs | DET-03 | Requires known-size eggs | Measure real eggs, place in nest box, compare classification to actual sizes |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
