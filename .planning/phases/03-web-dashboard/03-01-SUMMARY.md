---
phase: 03-web-dashboard
plan: 01
subsystem: api
tags: [fastapi, websocket, uvicorn, pydantic, sqlite]

# Dependency graph
requires:
  - phase: 02-data-persistence
    provides: EggDatabaseLogger, EggRepository, SQLite schema for egg_events and collection_events
provides:
  - FastAPI app with dashboard/history/collection JSON APIs
  - WebSocket hub for real-time event broadcasting
  - Pydantic schemas for API contracts
  - Pipeline event_callback for WebSocket bridge
  - CLI serve subcommand for local-network dashboard
  - Manual collection_mode guard in pipeline
affects: [03-web-dashboard, 04-remote-access]

# Tech tracking
tech-stack:
  added: [fastapi, uvicorn, jinja2, httpx, pytest-asyncio, pydantic]
  patterns: [repository-backed API routes, WebSocket hub broadcast, event bridge callback, manual collection_mode guard]

key-files:
  created:
    - src/egg_counter/web/__init__.py
    - src/egg_counter/web/server.py
    - src/egg_counter/web/realtime.py
    - src/egg_counter/web/schemas.py
    - tests/test_web_api.py
    - tests/test_websocket.py
  modified:
    - pyproject.toml
    - config/settings.yaml
    - src/egg_counter/repository.py
    - src/egg_counter/pipeline.py
    - src/egg_counter/cli.py
    - tests/test_pipeline.py

key-decisions:
  - "Used async broadcast_json with sync bridge wrapper for pipeline callback compatibility"
  - "Manual collection_mode skips tracker-generated collection events in pipeline, only POST /api/collect persists"
  - "Dashboard snapshot post-collection running count uses MAX(timestamp) from collection_events"

patterns-established:
  - "Repository pattern: all web routes query through EggRepository, no raw SQL in route handlers"
  - "Event bridge: pipeline event_callback -> make_event_bridge() -> WebSocketHub.broadcast_json_sync()"
  - "WebSocket protocol: initial snapshot on connect, then push events as they occur"

requirements-completed: [DASH-01, DASH-02, DASH-03]

# Metrics
duration: 13min
completed: 2026-03-23
---

# Phase 3 Plan 01: Web Dashboard Backend Summary

**FastAPI server with dashboard/history/collection JSON APIs, WebSocket hub for live push, and CLI serve command for local-network access**

## Performance

- **Duration:** 13 min
- **Started:** 2026-03-23T15:14:01Z
- **Completed:** 2026-03-23T15:27:05Z
- **Tasks:** 3
- **Files modified:** 12

## Accomplishments
- FastAPI app with GET /api/dashboard, GET /api/history, POST /api/collect, GET /health, WebSocket /ws
- Repository extended with get_dashboard_snapshot (post-collection running count), get_history_records, get_best_day, get_top_size
- Pipeline event_callback fires on each logged event and bridges to WebSocket clients via make_event_bridge
- Manual collection_mode guards tracker-generated collection events from persisting in serve mode
- CLI serve subcommand with --model, --camera, --host, --port, --video, --config, --zone flags
- 18 tests passing: 9 API tests, 3 WebSocket tests, 6 pipeline tests

## Task Commits

Each task was committed atomically (TDD: test then feat):

1. **Task 1: Dependencies, config, and dashboard query primitives**
   - `b92217c` test(03-01): add failing tests for dashboard query primitives
   - `49a43bf` feat(03-01): add Phase 3 dependencies, server config, and dashboard query primitives

2. **Task 2: FastAPI app, WebSocket hub, and endpoints**
   - `f6577ae` test(03-01): add failing tests for FastAPI routes and WebSocket hub
   - `a256fd7` feat(03-01): create FastAPI app, WebSocket hub, and dashboard/history/collection endpoints

3. **Task 3: Pipeline event bridge, collection semantics, CLI serve**
   - `377492b` test(03-01): add failing tests for event_callback and manual collection_mode
   - `f1b480f` feat(03-01): wire pipeline events to WebSocket, add collection_mode guard and CLI serve

## Files Created/Modified
- `src/egg_counter/web/__init__.py` - Web dashboard package init
- `src/egg_counter/web/server.py` - FastAPI app factory, routes, event bridge, uvicorn runner
- `src/egg_counter/web/realtime.py` - WebSocketHub with connect/disconnect/broadcast
- `src/egg_counter/web/schemas.py` - Pydantic models: DashboardSnapshot, HistoryRecord, CollectionResponse
- `src/egg_counter/repository.py` - Extended with get_dashboard_snapshot, get_history_records, get_best_day, get_top_size
- `src/egg_counter/pipeline.py` - Added event_callback, collection_mode guard
- `src/egg_counter/cli.py` - Added serve subcommand
- `pyproject.toml` - Added fastapi, uvicorn, jinja2, httpx, pytest-asyncio
- `config/settings.yaml` - Added web_host, web_port, web_reload, dashboard_title, collection_mode
- `tests/test_web_api.py` - 9 tests covering API routes and repository queries
- `tests/test_websocket.py` - 3 tests covering WebSocket hub behavior
- `tests/test_pipeline.py` - 2 new tests for event_callback and manual collection_mode

## Decisions Made
- Used async broadcast_json for route contexts and sync broadcast_json_sync for pipeline callback (non-async) contexts
- Manual collection_mode skips tracker-generated collection events; only POST /api/collect persists collections
- Dashboard snapshot post-collection running count queries MAX(timestamp) from collection_events table

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- WebSocket tests initially hung due to async/sync mismatch in broadcast_json when called from Starlette TestClient threads. Resolved by splitting into async broadcast_json and sync broadcast_json_sync methods.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Backend APIs ready for Plan 02 frontend template wiring (Jinja2 HTML, CSS, JavaScript)
- WebSocket protocol established: initial snapshot on connect, push events on detection/collection
- All route contracts stable for frontend consumption

---
*Phase: 03-web-dashboard*
*Completed: 2026-03-23*

## Self-Check: PASSED

All 6 created files verified. All 6 commit hashes verified.
