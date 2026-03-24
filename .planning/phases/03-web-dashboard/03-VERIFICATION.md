---
phase: 03-web-dashboard
verified: 2026-03-24T00:00:00Z
status: human_needed
score: 5/5 must-haves verified
human_verification:
  - test: "Open http://<pi-ip>:8000 on a phone browser. Observe the dashboard."
    expected: "Today's egg count is shown, broken down into small/medium/large/jumbo size chips. No horizontal scrolling occurs."
    why_human: "CSS layout correctness and phone-viewport rendering cannot be asserted programmatically."
  - test: "While dashboard is open, trigger a detection event (or insert a row directly into egg_events). Watch for the dashboard to update."
    expected: "The count updates within a few seconds without a page refresh. A toast notification appears saying '1 new egg added'."
    why_human: "Real-time WebSocket push latency requires a live browser session."
  - test: "Tap the 'Collected' button on the dashboard and confirm the dialog."
    expected: "Today's count resets to 0, a toast confirms the collection, and the reset persists after a refresh."
    why_human: "Confirmation dialog interaction and post-collection snapshot correctness require a human in the browser."
  - test: "Navigate to /history on a phone browser. Apply size and date filters."
    expected: "Records appear newest-first. Filters narrow the list correctly. No horizontal scrolling occurs."
    why_human: "Filter interaction and mobile layout correctness require a browser session."
  - test: "Open /dashboard on a phone screen (< 720px viewport). Tap the hamburger icon."
    expected: "Navigation links are hidden behind the hamburger and expand vertically when tapped."
    why_human: "Hamburger nav toggle interaction is a browser-only behaviour."
---

# Phase 3: Web Dashboard Verification Report

**Phase Goal:** User can view live egg counts, manage collections, and see production trends from a phone browser on the local network
**Verified:** 2026-03-24
**Status:** human_needed — all automated checks pass; 5 browser-session checks remain
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Opening the dashboard shows today's running egg count broken down by size | VERIFIED | `get_dashboard_snapshot()` returns `today_total` and `today_by_size`; dashboard.html has `id="today-total"` and `id="size-{small,medium,large,jumbo}"` hooks wired in `dashboard.js` via `renderSnapshot()` |
| 2 | Dashboard updates within seconds without user refreshing | VERIFIED | `WebSocketHub.broadcast_json()` + `make_event_bridge()` pipeline callback broadcast `egg_detected` events; `dashboard.js` `connectWebSocket()` receives and calls `refreshAllPeriods()` |
| 3 | User can tap a "collected" action on the dashboard | VERIFIED | `id="collect-button"` in template; `handleCollect()` in `dashboard.js` calls `POST /api/dashboard/collect`; backend persists via `EggDatabaseLogger.log_eggs_collected()` and broadcasts updated snapshot |
| 4 | Dashboard is readable on a phone screen without horizontal scrolling | VERIFIED (partial) | `overflow-x: hidden` on html/body; `@media (max-width: 719px)` stacks all grids to single column; hamburger nav implemented. Final human validation required. |
| 5 | User can view historical egg production charts | VERIFIED | SVG inline line chart (`buildLineChart`) and bar chart (`buildBarChart`) in `dashboard.js`; history page at `/history` with `GET /api/history` filters. |

**Score:** 5/5 truths have automated evidence; 5 items require human browser validation.

---

### Required Artifacts

| Artifact | Expected | Exists | Substantive | Wired | Status |
|----------|----------|--------|-------------|-------|--------|
| `src/egg_counter/web/server.py` | FastAPI app, routes, collection, WebSocket | Yes | Yes (230 lines, `create_app`, `make_event_bridge`, all routes) | Yes (imported by CLI, templates mount static) | VERIFIED |
| `src/egg_counter/web/realtime.py` | WebSocketHub and broadcast helpers | Yes | Yes (`connect`, `disconnect`, `broadcast_json`, `broadcast_json_sync`, `build_snapshot_event`) | Yes (imported in server.py, used in ws endpoint and event bridge) | VERIFIED |
| `src/egg_counter/web/schemas.py` | Canonical Pydantic models | Yes | Yes (`SizeBreakdown`, `BestDay`, `TopSize`, `ProductionPoint`, `DashboardSnapshot`, `HistoryRecord`, `CollectionResponse`) | Yes (importable; tests import indirectly via server) | VERIFIED |
| `src/egg_counter/web/templates/dashboard.html` | Mobile-first dashboard HTML | Yes | Yes (card-based layout, all id hooks, hamburger nav, SVG chart containers, toast div) | Yes (served by Jinja2 route, linked to dashboard.js and styles.css) | VERIFIED |
| `src/egg_counter/web/templates/history.html` | History page HTML | Yes | Yes (filter form, history-records container, hamburger nav) | Yes (served by Jinja2 route, linked to history.js and styles.css) | VERIFIED |
| `src/egg_counter/web/static/styles.css` | Mobile-first responsive CSS | Yes | Yes (`@media (max-width: 719px)` single-column stacking, hamburger rules, `overflow-x: hidden`) | Yes (linked from both templates via Jinja2 `url_for`) | VERIFIED |
| `src/egg_counter/web/static/dashboard.js` | Snapshot fetch, WebSocket, charts, collect | Yes | Yes (`loadSnapshot`, `connectWebSocket`, `handleCollect`, `buildLineChart`, `buildBarChart`, `showToast`) | Yes (loaded via `<script defer>` in dashboard.html) | VERIFIED |
| `src/egg_counter/web/static/history.js` | Filter state, API calls, record rendering | Yes | Yes (`loadHistory`, `renderHistory`, `applyFiltersToInputs`, `syncUrl`) | Yes (loaded via `<script defer>` in history.html) | VERIFIED |
| `tests/test_web_api.py` | HTTP/API coverage | Yes | Yes (9 tests: snapshot, filters, collection, health) | Yes (passing: 18 backend tests pass) | VERIFIED |
| `tests/test_websocket.py` | WebSocket coverage | Yes | Yes (3 tests: initial snapshot, event build, disconnect cleanup) | Yes (passing) | VERIFIED |
| `tests/test_dashboard_assets.py` | Template/asset assertions | Yes | Yes (5 tests: template sections, HTML hooks, JS contracts, CSS mobile guards, history assets) | Yes (passing) | VERIFIED |

---

### Key Link Verification

| From | To | Via | Status | Evidence |
|------|----|-----|--------|----------|
| `server.py` | `repository.py` | Dashboard/history routes call `EggRepository` methods | WIRED | `_load_snapshot()` calls `EggRepository.get_dashboard_snapshot()`; `api_history()` calls `EggRepository.get_history_records()` |
| `pipeline.py` | `web/realtime.py` | `event_callback` -> `make_event_bridge()` -> `WebSocketHub.broadcast_json_sync()` | WIRED | `EggCounterPipeline.__init__` accepts `event_callback`; `process_frame()` calls it on each `log_entry`; CLI `serve` command wires `make_event_bridge(app)` as the callback |
| `server.py` | `db.py` | Collection endpoint calls `EggDatabaseLogger.log_eggs_collected()` | WIRED | `api_collect()` directly instantiates `EggDatabaseLogger(db_path)` and calls `log_eggs_collected(count)` |
| `dashboard.js` | `/api/dashboard/snapshot` | `loadSnapshot()` / `refreshAllPeriods()` fetch | WIRED | Line 192: `fetch('/api/dashboard/snapshot?period=...')` |
| `dashboard.js` | `/ws/dashboard` | `connectWebSocket()` WebSocket connection | WIRED | Line 237: `new WebSocket('.../ws/dashboard')` |
| `dashboard.js` | `/api/dashboard/collect` | `handleCollect()` POST | WIRED | Line 262: `fetch('/api/dashboard/collect', {method: 'POST'})` |
| `history.js` | `/api/history` | `loadHistory()` fetch with filter params | WIRED | Line 97: `fetch('/api/history?' + params.toString())` |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `dashboard.html` + `dashboard.js` | `snapshot.today_total`, `today_by_size` | `GET /api/dashboard/snapshot` -> `EggRepository.get_dashboard_snapshot()` -> `SELECT` from `egg_events` / `collection_events` | Yes — SQL COUNT queries with post-collection filtering | FLOWING |
| `dashboard.js` (production chart) | `snapshot.production_series` | `EggRepository.get_eggs_by_date_range()` -> `SELECT detected_date, COUNT(*)` | Yes | FLOWING |
| `dashboard.js` (size chart) | `snapshot.size_breakdown` | `EggRepository.get_size_breakdown()` -> `SELECT size, COUNT(*)` | Yes | FLOWING |
| `history.html` + `history.js` | `records` array | `GET /api/history` -> `EggRepository.get_history_records()` -> `SELECT ... ORDER BY timestamp DESC` | Yes | FLOWING |
| WebSocket push | `event.snapshot` | `make_event_bridge()` -> `EggRepository.get_dashboard_snapshot()` on each pipeline event | Yes — same real DB query path | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 18 backend tests pass | `conda run -n egg-sentry python -m pytest tests/test_web_api.py tests/test_websocket.py tests/test_pipeline.py -x -q` | 18 passed in 4.78s | PASS |
| Dashboard asset tests pass | `conda run -n egg-sentry python -m pytest tests/test_dashboard_assets.py -x -q` | 5 passed in 0.02s | PASS |
| Full test suite clean | `conda run -n egg-sentry python -m pytest tests/ -x -q` | 91 passed, 1 skipped in 7.01s | PASS |
| Module imports cleanly | `python -c "from egg_counter.web.server import create_app; ..."` | `web app ok`, `hub ok`, `repository ok` | PASS |
| CLI `serve --help` | `python -m egg_counter.cli serve --help` | All 7 flags listed (--model, --camera, --config, --zone, --video, --host, --port) | PASS |
| Live server + phone browser | Requires running server on Pi | Cannot test without Pi hardware | SKIP (human required) |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| DASH-01 | 03-01-PLAN.md | View today's running egg count broken down by size | SATISFIED | `get_dashboard_snapshot()` returns `today_total` + `today_by_size`; template has size chip DOM hooks; `renderSnapshot()` populates them |
| DASH-02 | 03-01-PLAN.md | Dashboard updates in real-time via WebSocket | SATISFIED | WebSocketHub + `make_event_bridge()` pipeline callback; `connectWebSocket()` in `dashboard.js` reconnects on close (1.5s backoff) |
| DASH-03 | 03-01-PLAN.md | User can mark eggs as collected via dashboard action | SATISFIED | "Collected" button in template; `POST /api/dashboard/collect` persists event and returns updated snapshot; test asserts `today_total == 0` post-collection |
| DASH-04 | 03-02-SUMMARY.md (implied from plan 02) | Dashboard is mobile-responsive for phone viewing | SATISFIED (automated) / needs human | `@media (max-width: 719px)` single-column CSS, hamburger nav, `overflow-x: hidden`, `meta viewport` tag; test_dashboard_assets.py confirms CSS guards programmatically; visual validation needs human |

**Note on DASH-04:** REQUIREMENTS.md marks DASH-04 as `Pending` (not checked), yet the SUMMARY for plan 02 claims it as `requirements-completed: [DASH-01, DASH-02, DASH-03, DASH-04]`. The automated evidence (CSS breakpoints, single-column stacking, hamburger nav, viewport meta tag) substantiates that the implementation is in place. The `Pending` status in REQUIREMENTS.md should be updated after human phone-browser confirmation.

**Note on DATA-01:** REQUIREMENTS.md maps DATA-01 (historical production charts) to Phase 2, but the history page and production trend charts are delivered in Phase 3. The production trend chart (`/dashboard`) and full history log (`/history`) satisfy the observable intent of DATA-01. This is an attribution discrepancy in the REQUIREMENTS.md traceability table — no implementation gap exists.

---

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `dashboard.html:28-29` | `class="is-stub"` on "Modify Camera" and "Logout" nav buttons, `aria-disabled="true"` | Info | These are explicitly disabled future-phase links (v2 scope per REQUIREMENTS.md). They do not route anywhere and are not wired to any behaviour. No blocker for Phase 3 goals. |

No TODOs, FIXMEs, empty handlers, or disconnected data paths found.

---

### Human Verification Required

#### 1. Live Count Display on Phone Browser

**Test:** Navigate to `http://<pi-ip>:8000` on a phone (iOS Safari or Android Chrome).
**Expected:** Today's egg count shows in the "TODAY'S EGGS" KPI and in the summary pill. Size breakdown chips show per-size counts. No horizontal scroll bar appears.
**Why human:** CSS rendering correctness on a real phone viewport cannot be asserted from Python tests.

#### 2. Real-Time WebSocket Update

**Test:** With dashboard open on phone, insert an egg event into the database (or run detection against a video). Watch the dashboard for 5-10 seconds.
**Expected:** The count increments and a toast "1 new egg added" appears without a manual page refresh.
**Why human:** Requires a live browser session connected to a running server.

#### 3. Collection Flow End-to-End

**Test:** Tap the "Collected" button. Confirm the dialog. Observe the count.
**Expected:** Today's count resets to 0, a toast confirms the collection. After a full page refresh, count is still 0 (persisted).
**Why human:** Browser dialog (`window.confirm`) interaction and post-collect persistence round-trip require a live session.

#### 4. History Page Filters

**Test:** Navigate to `/history` on phone. Select a size filter and apply from/to dates.
**Expected:** Records filter correctly, count in top-right updates, newest-first ordering maintained. No horizontal scroll.
**Why human:** Filter interaction and mobile layout are browser-only behaviours.

#### 5. Hamburger Nav on Phone

**Test:** Open the dashboard on a phone screen (< 720px). Tap the three-bar icon.
**Expected:** Navigation links are hidden by default and expand vertically into a stacked list when the icon is tapped.
**Why human:** CSS toggle (`is-open` class) and touch interaction require a real browser.

---

### Summary

Phase 3 backend and frontend are fully implemented and connected:

- **FastAPI server** with dashboard, history, collection, health, and WebSocket routes, all backed by real SQLite queries through `EggRepository` — no raw SQL in route handlers, no static return values.
- **Pipeline event bridge** wires `EggCounterPipeline.event_callback` to `WebSocketHub.broadcast_json_sync()`, so live detections push to all connected browser clients.
- **Mobile-first UI** with responsive single-column CSS breakpoint at 720px, hamburger nav, SVG inline charts, and a `window.confirm` collection flow.
- **91 tests pass** (18 backend + 5 asset + remaining suite). No regressions.
- **CLI `serve` command** is functional with all 7 flags, enabling a one-command launch on the Pi.

The only remaining items are browser-session verifications (items 1–5 above) which cannot be automated. All programmatic checks for DASH-01 through DASH-04 pass.

---

_Verified: 2026-03-24_
_Verifier: Claude (gsd-verifier)_
