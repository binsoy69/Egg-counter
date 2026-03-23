# Phase 2: Data Persistence - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Egg detection events are durably stored in a SQLite database on the Pi's SD card, surviving reboots and power loss. Today's count resumes correctly after restart. Historical egg production data is queryable by day and by size category through a Python API that Phase 3 will consume.

</domain>

<decisions>
## Implementation Decisions

### Migration Strategy
- **D-01:** Replace `EggEventLogger` (JSONL) with a new SQLite-backed logger class. JSONL files stop being written.
- **D-02:** New logger keeps the same interface (`log_egg_detected()`, `log_eggs_collected()` methods with same signatures) so `pipeline.py` needs only an import swap — drop-in replacement.

### Reboot Resume
- **D-03:** On startup, query SQLite for today's egg count (`SELECT COUNT(*) WHERE date = today`) to restore the running count. Single source of truth — no checkpoint files.
- **D-04:** This works alongside the existing `_initialize_existing_eggs()` in `pipeline.py` which handles not re-counting visible eggs after restart.

### Query Interface
- **D-05:** Python repository/DAO class with methods like `get_daily_summary()`, `get_eggs_by_date_range()`, `get_size_breakdown()`. Phase 3 dashboard imports and calls these directly.
- **D-06:** No CLI query commands in this phase — queries are programmatic only.

### Storage Configuration
- **D-07:** Database path configurable via `db_path` key in `settings.yaml`, defaulting to `data/eggs.db` relative to project directory.
- **D-08:** Storage is the Pi's SD card (not USB SSD). No mount checks or fallback paths needed.
- **D-09:** Fail fast on startup if the configured DB path is not writable — clear error message, no silent fallback.

### Claude's Discretion
- SQLite schema design (table structure, indexes, constraints)
- WAL mode or other SQLite pragmas for reliability
- Whether to use raw sqlite3 or a lightweight ORM
- Exact method signatures on the query/DAO class beyond the named methods
- Migration/versioning approach for the schema

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project requirements
- `.planning/REQUIREMENTS.md` — DATA-01 defines historical data query requirement for this phase
- `.planning/ROADMAP.md` §Phase 2 — Phase goal, success criteria, dependency on Phase 1
- `.planning/PROJECT.md` — Hardware constraints (Pi 5, SD card storage), core value statement

### Phase 1 integration
- `.planning/phases/01-detection-pipeline/01-CONTEXT.md` — D-13 through D-18 define the event format and logging decisions that this phase replaces
- `src/egg_counter/logger.py` — Current JSONL logger being replaced (interface to preserve)
- `src/egg_counter/pipeline.py` — Integration point: calls `self.logger.log_egg_detected()` and `self.logger.log_eggs_collected()`
- `src/egg_counter/config.py` — Settings loader where `db_path` config will be added

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `EggEventLogger` interface (`log_egg_detected`, `log_eggs_collected` methods) — new SQLite logger must match these signatures
- `config.py` (`load_settings`) — YAML config loader, add `db_path` key here
- `settings.yaml` — existing config file, add `db_path` entry

### Established Patterns
- src-layout Python package (`src/egg_counter/`)
- YAML for settings, JSON for zone config
- UTC timestamps throughout (`datetime.now(timezone.utc).isoformat()`)
- Pipeline orchestrator pattern in `pipeline.py` — instantiates components and wires them together

### Integration Points
- `pipeline.py` line 44: `self.logger = EggEventLogger(...)` — swap to new SQLite logger here
- `pipeline.py` `process_frame()` — calls logger methods, returns event dicts (same contract)
- Phase 3 (Web Dashboard) will import the query/DAO class to serve dashboard data

</code_context>

<specifics>
## Specific Ideas

- Storage is SD card only — no USB SSD, so default path of `data/eggs.db` is appropriate
- The ROADMAP success criteria mention "USB SSD" but user clarified it's SD card — update roadmap accordingly
- Existing `_initialize_existing_eggs()` in pipeline handles visual re-detection; DB query handles count restoration — two complementary mechanisms

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-data-persistence*
*Context gathered: 2026-03-23*
