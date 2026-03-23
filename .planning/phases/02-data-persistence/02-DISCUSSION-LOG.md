# Phase 2: Data Persistence - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-23
**Phase:** 02-data-persistence
**Areas discussed:** Migration strategy, Reboot resume, Query interface, Storage config

---

## Migration Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Replace logger (Recommended) | Swap EggEventLogger for a new SQLite-backed logger with the same interface. Pipeline code changes minimally. JSONL files stop being written. | ✓ |
| Dual-write | Write to both SQLite and JSONL. Keeps JSONL as human-readable backup. | |
| SQLite primary + JSONL export | SQLite is the source of truth. Add a CLI command to export JSONL from SQLite if needed. | |

**User's choice:** Replace logger
**Notes:** None

### Follow-up: Interface Preservation

| Option | Description | Selected |
|--------|-------------|----------|
| Same interface (Recommended) | Drop-in replacement — same method signatures, pipeline.py just swaps the import. | ✓ |
| New interface | Redesign the logger API while we're at it. More flexibility but more pipeline changes. | |

**User's choice:** Same interface
**Notes:** None

---

## Reboot Resume

| Option | Description | Selected |
|--------|-------------|----------|
| Query DB on startup (Recommended) | On startup, query SQLite for today's egg count. Simple, single source of truth. | ✓ |
| Checkpoint file | Periodically write current count to a small file. Faster startup but second source of truth. | |
| Dashboard derives it | Don't resume in the pipeline at all — let the dashboard query the DB. | |

**User's choice:** Query DB on startup
**Notes:** None

---

## Query Interface

| Option | Description | Selected |
|--------|-------------|----------|
| Python API (Recommended) | Repository/DAO class with methods like get_daily_summary(), get_eggs_by_date_range(). Phase 3 imports these. | ✓ |
| CLI commands | Add CLI subcommands like 'egg-counter history --days 7'. Dashboard would still need Python API underneath. | |
| Both API + CLI | Python API as core, thin CLI wrapper on top. Most versatile but more code. | |

**User's choice:** Python API
**Notes:** None

---

## Storage Config

| Option | Description | Selected |
|--------|-------------|----------|
| Configurable in settings.yaml (Recommended) | Add a db_path key to settings.yaml, defaulting to 'data/eggs.db'. Follows existing config pattern. | ✓ |
| Fixed USB SSD path | Hardcode /mnt/ssd/eggs.db or similar. Less portable. | |
| XDG data directory | Use platform-appropriate data dir. More 'correct' but less obvious for Pi appliance. | |

**User's choice:** Configurable in settings.yaml
**Notes:** None

### Follow-up: Failure Behavior

**User's choice:** Storage is SD card only, not USB SSD. No mount checks needed.
**Notes:** User clarified that the Pi uses SD card storage, not a USB SSD as mentioned in the roadmap. Default path of data/eggs.db is appropriate. Fail fast if path not writable.

---

## Claude's Discretion

- SQLite schema design (table structure, indexes, constraints)
- WAL mode or other SQLite pragmas for reliability
- Whether to use raw sqlite3 or a lightweight ORM
- Exact method signatures on the query/DAO class
- Migration/versioning approach for the schema

## Deferred Ideas

None — discussion stayed within phase scope
