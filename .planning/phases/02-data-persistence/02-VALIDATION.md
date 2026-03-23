---
phase: 2
slug: data-persistence
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-23
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3.4 |
| **Config file** | `pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `pytest tests/test_db.py tests/test_repository.py -x` |
| **Full suite command** | `pytest tests/ -x` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_db.py tests/test_repository.py -x`
- **After every plan wave:** Run `pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 0 | DATA-01a | unit | `pytest tests/test_db.py::TestEggDatabaseLogger::test_log_egg_detected_persists -x` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 0 | DATA-01b | unit | `pytest tests/test_db.py::TestEggDatabaseLogger::test_count_restores_on_restart -x` | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 0 | DATA-01c | unit | `pytest tests/test_db.py::TestEggDatabaseLogger::test_log_eggs_collected -x` | ❌ W0 | ⬜ pending |
| 02-01-04 | 01 | 0 | DATA-01d | unit | `pytest tests/test_repository.py::TestEggRepository::test_get_daily_summary -x` | ❌ W0 | ⬜ pending |
| 02-01-05 | 01 | 0 | DATA-01e | unit | `pytest tests/test_repository.py::TestEggRepository::test_get_eggs_by_date_range -x` | ❌ W0 | ⬜ pending |
| 02-01-06 | 01 | 0 | DATA-01f | unit | `pytest tests/test_repository.py::TestEggRepository::test_get_size_breakdown -x` | ❌ W0 | ⬜ pending |
| 02-01-07 | 01 | 0 | DATA-01g | unit | `pytest tests/test_db.py::TestEggDatabaseLogger::test_fail_fast_unwritable -x` | ❌ W0 | ⬜ pending |
| 02-01-08 | 01 | 1 | DATA-01h | integration | `pytest tests/test_pipeline.py -x` | ✅ (needs update) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_db.py` — stubs for DATA-01a, DATA-01b, DATA-01c, DATA-01g
- [ ] `tests/test_repository.py` — stubs for DATA-01d, DATA-01e, DATA-01f
- [ ] `tests/conftest.py` — add `tmp_db_path` fixture for SQLite temp databases
- [ ] `tests/test_pipeline.py` — update logger reference for integration test

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Database survives Pi reboot | DATA-01b | Requires physical hardware power cycle | 1. Run pipeline, detect eggs. 2. Power off Pi. 3. Power on, verify count resumes. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
