# Phase 2: Data Persistence - Research

**Researched:** 2026-03-23
**Domain:** SQLite data persistence for egg detection events on Raspberry Pi
**Confidence:** HIGH

## Summary

This phase replaces the JSONL-based `EggEventLogger` with a SQLite-backed logger that preserves the same interface (`log_egg_detected`, `log_eggs_collected`). Python's built-in `sqlite3` module is sufficient -- no ORM needed for this simple schema. The database lives on the Pi's SD card at a configurable path (`data/eggs.db` by default).

The critical concerns are: (1) durability on power loss (solved by WAL mode + synchronous=FULL), (2) correct startup count restoration from SQLite (a single query replacing checkpoint files), and (3) a clean query/DAO class that Phase 3's dashboard can import directly. The existing test infrastructure (pytest 8.3.4, conftest.py with tmp_path fixtures) supports testing with in-memory or temp-file SQLite databases.

**Primary recommendation:** Use Python stdlib `sqlite3` with WAL journal mode and synchronous=FULL. Single connection held by the logger instance. Schema versioning via a `schema_version` pragma. Drop-in replacement of `EggEventLogger` with identical method signatures.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Replace `EggEventLogger` (JSONL) with a new SQLite-backed logger class. JSONL files stop being written.
- **D-02:** New logger keeps the same interface (`log_egg_detected()`, `log_eggs_collected()` methods with same signatures) so `pipeline.py` needs only an import swap -- drop-in replacement.
- **D-03:** On startup, query SQLite for today's egg count (`SELECT COUNT(*) WHERE date = today`) to restore the running count. Single source of truth -- no checkpoint files.
- **D-04:** This works alongside the existing `_initialize_existing_eggs()` in `pipeline.py` which handles not re-counting visible eggs after restart.
- **D-05:** Python repository/DAO class with methods like `get_daily_summary()`, `get_eggs_by_date_range()`, `get_size_breakdown()`. Phase 3 dashboard imports and calls these directly.
- **D-06:** No CLI query commands in this phase -- queries are programmatic only.
- **D-07:** Database path configurable via `db_path` key in `settings.yaml`, defaulting to `data/eggs.db` relative to project directory.
- **D-08:** Storage is the Pi's SD card (not USB SSD). No mount checks or fallback paths needed.
- **D-09:** Fail fast on startup if the configured DB path is not writable -- clear error message, no silent fallback.

### Claude's Discretion
- SQLite schema design (table structure, indexes, constraints)
- WAL mode or other SQLite pragmas for reliability
- Whether to use raw sqlite3 or a lightweight ORM
- Exact method signatures on the query/DAO class beyond the named methods
- Migration/versioning approach for the schema

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATA-01 | User can view historical egg production charts over days and weeks | Query/DAO class with `get_daily_summary()`, `get_eggs_by_date_range()`, `get_size_breakdown()` methods returning data suitable for charting. Schema includes indexed `detected_date` column for efficient date-range queries. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| sqlite3 (stdlib) | Ships with Python 3.13 (SQLite 3.45.3) | Database engine and Python binding | Zero dependencies. Built into Python. Sufficient for single-writer low-throughput use case (a few writes per hour). |
| pyyaml | >=6.0 (already installed) | Config loading for `db_path` | Already in project dependencies |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | >=8.0 (8.3.4 installed) | Testing SQLite logger and DAO | All tests -- use `:memory:` or `tmp_path` databases |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| raw sqlite3 | peewee ORM | Adds a dependency for 2 tables. Overkill for this schema complexity. |
| raw sqlite3 | SQLAlchemy | Way too heavy for embedded Pi use case with 2 tables. |
| sqlite3 | TinyDB | Not SQL-queryable. Would make Phase 3 queries harder. |

**Installation:**
No new packages needed. `sqlite3` is in the Python standard library.

## Architecture Patterns

### Recommended Project Structure
```
src/egg_counter/
    db.py              # SQLite logger (replaces JSONL logger)
    repository.py      # Query/DAO class for Phase 3 consumption
    logger.py          # Kept as-is (not imported anymore by pipeline)
```

### Pattern 1: Drop-In Logger Replacement
**What:** New `EggDatabaseLogger` class in `db.py` matching `EggEventLogger` interface exactly.
**When to use:** This is the primary pattern -- `pipeline.py` swaps one import.

```python
# db.py
import sqlite3
from datetime import datetime, timezone, date
from pathlib import Path


class EggDatabaseLogger:
    """SQLite-backed egg event logger. Drop-in replacement for EggEventLogger."""

    def __init__(self, db_path: str = "data/eggs.db") -> None:
        db_file = Path(db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)

        # Fail fast if path not writable (D-09)
        if db_file.exists() and not os.access(db_file, os.W_OK):
            raise PermissionError(f"Database not writable: {db_path}")
        if not db_file.exists() and not os.access(db_file.parent, os.W_OK):
            raise PermissionError(f"Cannot create database at: {db_path}")

        self.conn = sqlite3.connect(db_path)
        self._configure_pragmas()
        self._create_tables()

        # Restore today's count from DB (D-03)
        self.egg_count = self._get_today_count()

    def _configure_pragmas(self) -> None:
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=FULL")
        self.conn.execute("PRAGMA foreign_keys=ON")

    def log_egg_detected(
        self,
        track_id: int,
        size: str,
        confidence: float,
        bbox: list,
        size_method: str,
        raw_measurement_mm: float,
        frame_number: int,
    ) -> dict:
        # Same signature as EggEventLogger
        ...

    def log_eggs_collected(self, count: int) -> dict:
        # Same signature as EggEventLogger
        ...
```

### Pattern 2: Separate Query/DAO Class
**What:** `EggRepository` class in `repository.py` provides read-only query methods for Phase 3.
**When to use:** Phase 3 dashboard imports this to serve data.

```python
# repository.py
class EggRepository:
    """Read-only query interface for egg event data."""

    def __init__(self, db_path: str = "data/eggs.db") -> None:
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row  # dict-like access

    def get_daily_summary(self, target_date: date) -> dict:
        """Return total count and size breakdown for a given date."""
        ...

    def get_eggs_by_date_range(self, start: date, end: date) -> list[dict]:
        """Return daily totals for a date range (for charting)."""
        ...

    def get_size_breakdown(self, start: date, end: date) -> dict:
        """Return egg counts grouped by size category for a date range."""
        ...
```

### Pattern 3: Schema Versioning via user_version Pragma
**What:** Use SQLite's `PRAGMA user_version` to track schema version. Check on startup, apply migrations if needed.
**When to use:** Every startup -- check version and migrate forward.

```python
SCHEMA_VERSION = 1

def _check_schema_version(self) -> None:
    current = self.conn.execute("PRAGMA user_version").fetchone()[0]
    if current < SCHEMA_VERSION:
        self._migrate(current)
    self.conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
```

### Anti-Patterns to Avoid
- **Opening/closing connections per write:** SQLite connection setup has overhead. Keep one connection for the logger's lifetime. Close in a `close()` method or `__del__`.
- **Using autocommit for everything:** Use explicit transactions for the write operations. The `with conn:` context manager handles commit/rollback correctly.
- **Storing dates as strings without a consistent format:** Always use ISO 8601 format for timestamps and `YYYY-MM-DD` for date columns. SQLite date functions expect this.
- **Forgetting to index the date column:** Daily queries will be the primary access pattern. An index on `detected_date` is essential.

## Schema Design (Claude's Discretion)

### Recommended Schema

```sql
CREATE TABLE IF NOT EXISTS egg_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,           -- ISO 8601 UTC
    detected_date TEXT NOT NULL,       -- YYYY-MM-DD (UTC date, for indexing)
    track_id INTEGER NOT NULL,
    size TEXT NOT NULL,                -- small, medium, large, jumbo
    confidence REAL NOT NULL,
    bbox_x1 REAL NOT NULL,
    bbox_y1 REAL NOT NULL,
    bbox_x2 REAL NOT NULL,
    bbox_y2 REAL NOT NULL,
    size_method TEXT NOT NULL,
    raw_measurement_mm REAL NOT NULL,
    frame_number INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_egg_events_date ON egg_events(detected_date);
CREATE INDEX IF NOT EXISTS idx_egg_events_size ON egg_events(detected_date, size);

CREATE TABLE IF NOT EXISTS collection_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,           -- ISO 8601 UTC
    collected_date TEXT NOT NULL,      -- YYYY-MM-DD (UTC date)
    count INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_collection_date ON collection_events(collected_date);
```

**Design rationale:**
- Separate tables for egg detections and collections (different schemas, different query patterns)
- `detected_date` column denormalizes the date from the timestamp for fast indexed lookups -- avoids `substr()` or `date()` in WHERE clauses
- bbox stored as 4 separate columns (not JSON) for potential future filtering
- No foreign keys between tables (events are independent)

### Key Queries

```sql
-- D-03: Today's count for startup restoration
SELECT COUNT(*) FROM egg_events WHERE detected_date = date('now');

-- DATA-01: Daily summary
SELECT detected_date, size, COUNT(*) as count
FROM egg_events
WHERE detected_date BETWEEN ? AND ?
GROUP BY detected_date, size
ORDER BY detected_date;

-- DATA-01: Daily totals for charting
SELECT detected_date, COUNT(*) as total
FROM egg_events
WHERE detected_date BETWEEN ? AND ?
GROUP BY detected_date
ORDER BY detected_date;
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Date parsing/formatting | Custom date string manipulation | `datetime.fromisoformat()` and `.isoformat()` | Edge cases with timezones, DST |
| Schema migration framework | Full Alembic-style migration system | `PRAGMA user_version` + simple if/elif migration chain | Only 2 tables, v1 schema. Lightweight is better here. |
| Connection pooling | Thread-local connection pool | Single `sqlite3.connect()` per instance | Single-threaded pipeline. One writer, separate reader for DAO. |
| JSON serialization of bbox | Custom serialize/deserialize | Store as 4 separate REAL columns | Avoids json.loads() on every query, enables future SQL filtering |

## Common Pitfalls

### Pitfall 1: WAL mode + synchronous=NORMAL loses data on power loss
**What goes wrong:** With WAL + synchronous=NORMAL (the commonly recommended "fast" setting), committed transactions can be lost if power is cut before the WAL is checkpointed to the main database.
**Why it happens:** NORMAL only syncs during checkpoint, not after each commit. On sudden power loss, the WAL file may be corrupted.
**How to avoid:** Use `PRAGMA synchronous=FULL` with WAL mode. This syncs the WAL after each commit. Slightly slower but guarantees durability -- critical for a Pi that may lose power.
**Warning signs:** Missing egg events after a power cycle.

### Pitfall 2: SQLite date functions use UTC by default
**What goes wrong:** `date('now')` returns UTC date. If the Pi is in a western-hemisphere timezone, eggs detected at 11pm local time get a different UTC date than the user expects for "today."
**Why it happens:** SQLite's built-in date functions operate in UTC. The project already uses UTC timestamps (established pattern).
**How to avoid:** Store `detected_date` as UTC date consistently. Phase 3 dashboard handles timezone display. The `_get_today_count()` method must use UTC date to match.
**Warning signs:** Count mismatch after midnight UTC but before midnight local time.

### Pitfall 3: Forgetting to commit after writes
**What goes wrong:** Inserts silently succeed in memory but never persist to disk.
**Why it happens:** Python's sqlite3 module uses implicit transactions. Without `conn.commit()` or `with conn:` context manager, data stays in a transaction.
**How to avoid:** Always use `with self.conn:` context manager for write operations -- it auto-commits on success, auto-rolls-back on exception.
**Warning signs:** Data present during session but gone after restart.

### Pitfall 4: Connection not closed on pipeline shutdown
**What goes wrong:** WAL file not properly checkpointed, potential data in buffer not flushed.
**Why it happens:** Pipeline uses Ctrl+C to stop, `finally` block in `run()` may not call logger cleanup.
**How to avoid:** Add a `close()` method to the logger. Call it from pipeline's `finally` block. Also consider `atexit.register()` as a safety net.
**Warning signs:** Growing WAL file size, stale `-shm` and `-wal` files.

### Pitfall 5: Existing test mocking patterns break with new logger
**What goes wrong:** Tests that mock `egg_counter.logger.datetime` need updating since the new logger is in `db.py`.
**Why it happens:** Import path changes when module changes.
**How to avoid:** New tests in `test_db.py` use `:memory:` SQLite databases with `tmp_path` fixtures. Don't need to mock datetime -- insert with known timestamps directly.
**Warning signs:** Test failures after import swap.

## Code Examples

### Connection setup with pragmas and table creation
```python
# Source: Python docs + SQLite docs
import sqlite3
from pathlib import Path

conn = sqlite3.connect("data/eggs.db")
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA synchronous=FULL")
conn.execute("PRAGMA foreign_keys=ON")

# Create tables
conn.executescript("""
    CREATE TABLE IF NOT EXISTS egg_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        detected_date TEXT NOT NULL,
        track_id INTEGER NOT NULL,
        size TEXT NOT NULL,
        confidence REAL NOT NULL,
        bbox_x1 REAL NOT NULL,
        bbox_y1 REAL NOT NULL,
        bbox_x2 REAL NOT NULL,
        bbox_y2 REAL NOT NULL,
        size_method TEXT NOT NULL,
        raw_measurement_mm REAL NOT NULL,
        frame_number INTEGER NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_egg_events_date ON egg_events(detected_date);
""")
conn.execute(f"PRAGMA user_version = 1")
```

### Insert with context manager (auto-commit)
```python
# Source: Python docs https://docs.python.org/3/library/sqlite3.html
with self.conn:
    self.conn.execute(
        """INSERT INTO egg_events
           (timestamp, detected_date, track_id, size, confidence,
            bbox_x1, bbox_y1, bbox_x2, bbox_y2,
            size_method, raw_measurement_mm, frame_number)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (ts, detected_date, track_id, size, confidence,
         bbox[0], bbox[1], bbox[2], bbox[3],
         size_method, raw_measurement_mm, frame_number),
    )
```

### Today's count restoration (D-03)
```python
def _get_today_count(self) -> int:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    row = self.conn.execute(
        "SELECT COUNT(*) FROM egg_events WHERE detected_date = ?",
        (today,),
    ).fetchone()
    return row[0]
```

### Pipeline integration (D-02)
```python
# In pipeline.py -- only change needed:
# Old:
from egg_counter.logger import EggEventLogger
self.logger = EggEventLogger(settings.get("log_dir", "logs"))

# New:
from egg_counter.db import EggDatabaseLogger
self.logger = EggDatabaseLogger(settings.get("db_path", "data/eggs.db"))
```

### Testing with in-memory database
```python
# In tests -- use :memory: for speed, tmp_path for persistence tests
def test_log_egg_detected_persists(tmp_path):
    db_path = str(tmp_path / "test.db")
    logger = EggDatabaseLogger(db_path)
    event = logger.log_egg_detected(
        track_id=1, size="large", confidence=0.95,
        bbox=[100.0, 100.0, 200.0, 200.0],
        size_method="bbox_ratio", raw_measurement_mm=58.3,
        frame_number=100,
    )
    # Verify persistence
    logger.close()
    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT * FROM egg_events").fetchall()
    assert len(rows) == 1
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| JSONL daily files | SQLite with WAL | This phase | Durable, queryable, survives power loss |
| Count from file parsing | COUNT(*) from SQLite | This phase | Single source of truth, instant on startup |
| No historical queries | DAO class with date range queries | This phase | Enables Phase 3 dashboard charting |

## Open Questions

1. **Timezone handling for "today"**
   - What we know: Project uses UTC throughout (established pattern). `detected_date` will be UTC date.
   - What's unclear: Whether the user considers "today" to be UTC midnight or local midnight. This affects the startup count restoration.
   - Recommendation: Use UTC consistently (matching existing pattern). Phase 3 can adjust display timezone. Document this behavior.

2. **Old JSONL data migration**
   - What we know: JSONL logger will stop being used. Old files remain on disk.
   - What's unclear: Whether to migrate existing JSONL data into SQLite.
   - Recommendation: Do not migrate. This is a hobby project with minimal historical data. Old JSONL files can be kept as-is for reference. Phase scope is forward-looking.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3.4 |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `pytest tests/test_db.py tests/test_repository.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DATA-01a | Egg events persist to SQLite | unit | `pytest tests/test_db.py::TestEggDatabaseLogger::test_log_egg_detected_persists -x` | Wave 0 |
| DATA-01b | Count restores correctly after "reboot" (new logger instance) | unit | `pytest tests/test_db.py::TestEggDatabaseLogger::test_count_restores_on_restart -x` | Wave 0 |
| DATA-01c | Collection events persist and reset count | unit | `pytest tests/test_db.py::TestEggDatabaseLogger::test_log_eggs_collected -x` | Wave 0 |
| DATA-01d | Daily summary query returns correct grouped data | unit | `pytest tests/test_repository.py::TestEggRepository::test_get_daily_summary -x` | Wave 0 |
| DATA-01e | Date range query returns daily totals | unit | `pytest tests/test_repository.py::TestEggRepository::test_get_eggs_by_date_range -x` | Wave 0 |
| DATA-01f | Size breakdown query groups by size category | unit | `pytest tests/test_repository.py::TestEggRepository::test_get_size_breakdown -x` | Wave 0 |
| DATA-01g | Fail fast on unwritable db_path | unit | `pytest tests/test_db.py::TestEggDatabaseLogger::test_fail_fast_unwritable -x` | Wave 0 |
| DATA-01h | Pipeline integration -- logger swap works end-to-end | integration | `pytest tests/test_pipeline.py -x` (updated) | Existing (needs update) |

### Sampling Rate
- **Per task commit:** `pytest tests/test_db.py tests/test_repository.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_db.py` -- covers DATA-01a, DATA-01b, DATA-01c, DATA-01g
- [ ] `tests/test_repository.py` -- covers DATA-01d, DATA-01e, DATA-01f
- [ ] Update `tests/conftest.py` -- add `tmp_db_path` fixture for SQLite temp databases
- [ ] Update `tests/test_pipeline.py` -- swap logger reference for integration test

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Everything | Yes | 3.13.5 (Anaconda) | -- |
| sqlite3 (stdlib) | Database | Yes | 3.45.3 | -- |
| pytest | Testing | Yes | 8.3.4 | -- |
| pyyaml | Config | Yes | Already in deps | -- |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** None.

## Sources

### Primary (HIGH confidence)
- [Python sqlite3 docs](https://docs.python.org/3/library/sqlite3.html) -- connection management, context managers, Row factory, pragmas
- [SQLite WAL documentation](https://www.sqlite.org/wal.html) -- WAL mode behavior, checkpoint, durability guarantees
- Existing codebase: `src/egg_counter/logger.py`, `pipeline.py`, `config.py` -- interface contracts, patterns

### Secondary (MEDIUM confidence)
- [SQLite durability settings analysis](https://www.agwa.name/blog/post/sqlite_durability) -- synchronous=FULL recommendation with WAL
- [Getting the most out of SQLite3 with Python](https://remusao.github.io/posts/few-tips-sqlite-perf.html) -- performance patterns
- [SQLite on Raspberry Pi forums](https://forums.raspberrypi.com/viewtopic.php?t=255573) -- SD card reliability experiences

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- stdlib sqlite3 is the obvious and only sensible choice for embedded Python + SQLite
- Architecture: HIGH -- drop-in replacement pattern is well-defined by existing interface, schema is straightforward
- Pitfalls: HIGH -- WAL + synchronous settings, connection lifecycle, and UTC date handling are well-documented concerns

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (stable domain, no fast-moving dependencies)
