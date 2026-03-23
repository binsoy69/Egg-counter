# Phase 3: Web Dashboard - Research

**Researched:** 2026-03-23
**Domain:** FastAPI-based local-network dashboard over the existing Raspberry Pi Python monolith
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
### Layout and Navigation
- Follow the provided dashboard and history mockups as the source of truth for the visual structure.
- Build this as a mobile-first responsive web app that also scales cleanly to larger screens.
- Primary navigation uses the mockup structure: `Dashboard`, `History`, `Modify Camera`, `Logout`.
- Dashboard layout is card-based with:
  - a top camera summary row
  - weekly / monthly / yearly summary cards
  - KPI cards for today's eggs, all time, best day, and top size
  - a daily egg production line chart
  - an egg size distribution bar chart
- History is a separate screen with filter controls and a newest-first record list.

### Live Update Behavior
- When a new egg is detected, the dashboard updates immediately and also shows a visible alert/toast.
- The alert copy should be count-focused: `1 new egg added`.
- The alert auto-dismisses after a few seconds.
- Weekly / monthly / yearly cards are interactive; tapping one updates the charts below rather than acting as display-only cards or navigation shortcuts.

### Collection Flow
- The required `Collected` action lives in the camera summary row.
- Tapping `Collected` should ask for confirmation before applying the reset.
- After confirmation, the dashboard should immediately reset the live count/cards and show a success message.
- Collection remains an all-eggs-at-once action, consistent with prior phase decisions.

### Trend and History Display
- Main dashboard charts should match the mockup structure exactly:
  - daily egg production line chart
  - egg size distribution bar chart
- History defaults to newest-first ordering.
- History filters for Phase 3 are exactly the mockup set: `size`, `from`, and `to`.
- No extra history controls are required for this phase unless implementation constraints force a minimal adaptation.

### Claude's Discretion
- Exact responsive breakpoints and how the desktop layout expands from the mobile-first baseline
- Visual styling details needed to faithfully implement the mockups
- Exact success-message wording after collection
- Exact toast animation/highlight treatment for live egg updates
- Whether `Modify Camera` and `Logout` render as disabled placeholders, informational links, or simple stubs if they are not fully implemented in this phase

### Deferred Ideas (OUT OF SCOPE)
- Predefined username/password authentication with no self-registration - separate capability, not required by the current Phase 3 roadmap entry
- `Modify Camera` as a full settings flow for cage count / chickens-per-cage changes - separate capability from the current Phase 3 success criteria; may be informational or stubbed unless explicitly added to roadmap
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DASH-01 | User can view today's running egg count broken down by size | Requires a collection-aware dashboard service/API; current `EggRepository.get_daily_summary()` counts all eggs for the day and does not reset after collection |
| DASH-02 | Dashboard updates in real-time via WebSocket when an egg is detected | Use FastAPI native WebSocket endpoints plus a thread-safe event bridge from the existing synchronous pipeline |
| DASH-03 | User can mark eggs as collected via a "collected" action on the dashboard | Add a POST collection endpoint that reuses existing collection-event persistence semantics and becomes the single UI-triggered reset path |
| DASH-04 | Dashboard is mobile-responsive for phone viewing | Serve same-origin static HTML/CSS/JS, mobile-first CSS grid/cards, and vendored Chart.js configured for responsive containers |
</phase_requirements>

## Summary

Phase 3 should stay inside the existing Python monolith. Add a FastAPI app that serves two static pages (`Dashboard` and `History`), exposes a small JSON API over the existing SQLite data, and publishes live updates through a native WebSocket endpoint. Do not introduce a separate frontend framework or a second backend service. The repo already has the critical foundations: SQLite persistence, `EggRepository` query helpers, and a persisted collection-event model.

The main planning risk is state consistency, not routing or UI polish. Two repo realities matter immediately: `src/egg_counter/pipeline.py` is synchronous and blocking, and `src/egg_counter/repository.py` is not yet collection-aware for "today's running count". If the planner ignores those, Phase 3 will either re-architect the runtime unnecessarily or ship a dashboard that shows the wrong count after the user taps `Collected`.

**Primary recommendation:** Build a same-origin FastAPI dashboard module with a thread-safe event bridge from the existing pipeline, and add a new collection-aware dashboard service instead of querying `EggRepository` directly from routes.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.135.1 | REST API, WebSocket endpoint, lifespan orchestration | Official docs cover WebSockets, lifespan, static files, and testing in one stack; fits the existing Python monolith cleanly |
| Uvicorn | 0.41.0 | ASGI server for FastAPI | Officially supports HTTP/1.1 and WebSockets; `uvicorn[standard]` brings the practical extras for local runtime |
| Python `sqlite3` | stdlib in Python 3.11+ | Reuse existing SQLite database access | Current repo already uses `sqlite3`; write/read volume is tiny and does not justify an async DB migration |
| Vanilla HTML/CSS/JS | browser-native | Dashboard and history UI | No build step, no Node toolchain, and clean deployment on the Pi |
| Chart.js | 4.5.1 | Daily trend line chart and size distribution bar chart | Mature, lightweight, and enough for the required charts without hand-building canvas logic |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 8.4.1 | Test runner | Keep existing test stack and extend it for web/API coverage |
| httpx | 0.28.1 | HTTP assertions through Starlette/FastAPI `TestClient` | Required for API and app-level tests |
| pytest-asyncio | 1.3.0 | Async helper tests | Use only if new async services or queue pumps get direct unit tests |
| Jinja2 | 3.1.x | Optional HTML templating | Only if you need server-rendered config injection; otherwise keep the UI as plain static files |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Vanilla HTML/CSS/JS | React/Vite | Faster component authoring for large UIs, but unnecessary build/deploy complexity for this two-screen dashboard |
| Native WebSocket | polling | Simpler to reason about, but violates the live-update requirement and wastes requests |
| Vendored Chart.js asset | CDN script tag | Slightly less repo churn, but adds an avoidable internet dependency to a local-network phase |
| Sync `sqlite3` service layer | `aiosqlite` | Better async ergonomics, but it would force a database-access rewrite the repo does not currently need |

**Installation:**
```bash
pip install fastapi==0.135.1 "uvicorn[standard]==0.41.0" httpx==0.28.1
pip install -U pytest==8.4.1 pytest-asyncio==1.3.0
```

Chart.js should be vendored into the repo from the official `v4.5.1` release asset and served locally by FastAPI, not loaded from a CDN.

**Version verification:** Verified on 2026-03-23 against official package/release pages: FastAPI `0.135.1` (PyPI, 2026-03-01), Uvicorn `0.41.0` (PyPI, 2026-02-16), Chart.js `4.5.1` (GitHub release, 2025-10-13), pytest `8.4.1` (PyPI, 2025-06-18), httpx `0.28.1` (PyPI, 2024-12-06), pytest-asyncio `1.3.0` (PyPI, 2025-11-10).

## Architecture Patterns

### Recommended Project Structure
```text
src/
- egg_counter/
  - web/
    - app.py              # FastAPI app factory + lifespan wiring
    - api.py              # JSON routes for summary, history, collection
    - ws.py               # WebSocket endpoint + connection manager
    - events.py           # Thread-safe bridge from pipeline -> asyncio
    - services.py         # Collection-aware dashboard query logic
    - schemas.py          # Response/request models
    - static/
      - dashboard.html
      - history.html
      - css/
      - js/
      - vendor/chart.umd.js
  - db.py                 # Existing write path and collection persistence
  - repository.py         # Existing historical queries; extend, don't bypass
  - pipeline.py           # Existing detection runtime, adapted to publish events
tests/
- test_web_api.py
- test_websocket.py
- test_dashboard_service.py
```

### Pattern 1: Same-Origin Dashboard App
**What:** Serve dashboard HTML, CSS, JS, JSON endpoints, and WebSocket from the same FastAPI app and origin.

**When to use:** Default for all of Phase 3.

**Example:**
```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory=static_dir), name="static")
```
Source: FastAPI Static Files docs, FastAPI Lifespan docs

Why this pattern:
- Avoids CORS entirely in production and local-network use.
- Keeps deployment to one Python process family.
- Matches the repo's current "single Pi, single app" architecture.

### Pattern 2: Thread-Safe Pipeline Event Bridge
**What:** Keep the detection pipeline synchronous, but publish detection and collection events into the FastAPI event loop through a queue owned by the web app.

**When to use:** When reusing the existing `EggCounterPipeline` rather than rewriting it to async.

**Example:**
```python
import asyncio


class DashboardEventBridge:
    def __init__(self) -> None:
        self.loop: asyncio.AbstractEventLoop | None = None
        self.queue: asyncio.Queue[dict] = asyncio.Queue()

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self.loop = loop

    def publish_from_pipeline(self, event: dict) -> None:
        if self.loop is None:
            return
        self.loop.call_soon_threadsafe(self.queue.put_nowait, event)


async def pump_dashboard_events(bridge, ws_manager, cache) -> None:
    while True:
        event = await bridge.queue.get()
        cache.apply(event)
        await ws_manager.broadcast(event)
```
Source: FastAPI lifespan guidance, Starlette WebSocket docs

Planning implication: routes and WebSocket handlers stay async, but the detector can remain mostly untouched except for publishing events after DB writes.

### Pattern 3: Dashboard Service Owns Count Semantics
**What:** Put dashboard-specific query logic in a service layer that uses `EggRepository` and collection metadata instead of letting routes assemble SQL or infer counts ad hoc.

**When to use:** For `today`, KPI cards, history filters, and collection reset responses.

**Example:**
```python
class DashboardService:
    def __init__(self, repository, db_logger) -> None:
        self.repository = repository
        self.db_logger = db_logger

    def get_running_today_summary(self, today):
        # Must exclude eggs detected before the latest same-day collection event.
        ...

    def mark_collected(self, count: int) -> dict:
        return self.db_logger.log_eggs_collected(count=count)
```
Source: repo analysis of `src/egg_counter/repository.py` and `src/egg_counter/db.py`

Planning implication: Phase 3 needs at least one new query/service abstraction beyond the current repository methods.

### Pattern 4: Reconcile UI State After WebSocket Events
**What:** Use WebSocket events for immediacy, but refresh summary/trend data from the API after meaningful events instead of only mutating DOM state optimistically.

**When to use:** On `egg_detected`, `eggs_collected`, reconnect, and period-card changes.

**Example:**
```javascript
socket.addEventListener("message", async (event) => {
  const payload = JSON.parse(event.data);
  showToast(payload.type === "egg_detected" ? "1 new egg added" : "Collection saved");
  await refreshSummary();
  await refreshCharts(activePeriod);
});
```
Source: project-specific inference from the repo's persistence model and reconnect risk

Why this pattern:
- Prevents drift after reconnects or missed events.
- Correctly handles collection resets and historical data changes.
- Keeps the frontend simple.

### Anti-Patterns to Avoid
- **Route-level ad hoc SQL:** extend repository/service code instead of embedding dashboard SQL into FastAPI routes.
- **Direct async rewrite of `pipeline.py` in Phase 3:** this expands scope for little gain; adapt with a bridge first.
- **Two collection authorities:** do not keep both tracker auto-collection and dashboard-confirmed collection active without a clear owner.
- **CDN-only Chart.js:** local-network viewing should not fail because the WAN is down.
- **Separate frontend dev server in production architecture:** same-origin serving is simpler and avoids CORS and deployment drift.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Real-time browser transport | Custom polling/retry protocol | Native FastAPI/Starlette WebSocket | Officially supported, lower complexity, fits single-user push updates |
| Charts | Canvas/SVG chart rendering from scratch | Chart.js | Responsive line/bar charts are already solved well |
| Static asset server | Custom file-serving routes | `StaticFiles` | Official FastAPI pattern; less code and fewer mistakes |
| App lifecycle startup/shutdown | Manual bootstrapping globals | FastAPI `lifespan` | Official current pattern for shared resources and background tasks |
| WebSocket integration tests | Homegrown socket harness | `TestClient` websocket support | Official testing path; works with the app directly |
| Dashboard count semantics | DOM-only optimistic counters | API-backed service layer + event reconciliation | Prevents count drift after collection/reset and reconnects |

**Key insight:** The deceptively hard problem in this phase is not rendering cards. It is keeping three truths aligned: persisted egg events, same-day collection resets, and live browser state. Reuse the repo's persistence model and official ASGI primitives instead of inventing new state channels.

## Common Pitfalls

### Pitfall 1: Using `get_daily_summary()` for the Running Count
**What goes wrong:** The dashboard shows the total eggs detected today, even after the user has tapped `Collected`.

**Why it happens:** `src/egg_counter/repository.py` groups all `egg_events` for a date and does not account for `collection_events`, while `src/egg_counter/db.py` clearly treats the running count as "after the latest same-day collection".

**How to avoid:** Add a collection-aware summary method or service for DASH-01. Do not expose `get_daily_summary()` as the "today" API unchanged.

**Warning signs:** After a collection action, the UI resets briefly and then jumps back to the pre-collection total after a refresh.

### Pitfall 2: Double-Logging Collection Events
**What goes wrong:** The user taps `Collected`, but the tracker also auto-detects "all eggs disappeared" and logs another collection event.

**Why it happens:** `src/egg_counter/tracker.py` already emits `{"action": "collected"}` after `collection_timeout`, while Phase 3 also requires a confirmed dashboard collection action.

**How to avoid:** Make one authority explicit in the plan. Recommended for Phase 3: dashboard-confirmed collection is authoritative for UI reset flow, and auto-collection is disabled or bypassed when the web dashboard runtime is active.

**Warning signs:** Duplicate collection rows for the same moment, wrong running count after confirmation, or counts unexpectedly zeroing without user action.

### Pitfall 3: Blocking the Event Loop With Pipeline Work
**What goes wrong:** WebSocket pushes stall, UI feels delayed, or API requests hang when detection is active.

**Why it happens:** The current pipeline is synchronous and uses blocking OpenCV reads plus `time.sleep()`.

**How to avoid:** Run the detector in a background thread/process and bridge events into FastAPI through a queue. Keep the ASGI loop focused on HTTP/WebSocket work.

**Warning signs:** New detections appear in logs immediately but the browser updates seconds later or only after reconnect.

### Pitfall 4: Charts Break on Mobile
**What goes wrong:** The line/bar charts overflow cards, render blurry, or collapse on narrow screens.

**Why it happens:** Chart.js resizes against its parent container, not the canvas itself, and defaults to maintaining aspect ratio.

**How to avoid:** Give each chart a dedicated, relatively positioned container and set `maintainAspectRatio: false` for dashboard cards.

**Warning signs:** Horizontal scrolling, shrinking canvases, or tiny unreadable charts on phones.

### Pitfall 5: Same-Origin Assumptions Broken During Development
**What goes wrong:** Fetches or WebSocket connections fail in the browser with origin or port issues.

**Why it happens:** A separate frontend origin introduces CORS and different host/port handling.

**How to avoid:** Plan production and development around the same FastAPI origin whenever possible. If a different origin is used temporarily, configure `CORSMiddleware` explicitly.

**Warning signs:** Browser console shows CORS errors, failing preflights, or WebSocket handshake issues against another port.

### Pitfall 6: UTC Date Buckets May Not Match the Farm's "Today"
**What goes wrong:** Counts and charts roll over at UTC midnight instead of the user's expected local day boundary.

**Why it happens:** The current persistence layer stores UTC timestamps and date fields.

**How to avoid:** Decide during planning whether Phase 3 presents UTC buckets as-is or translates query boundaries to a configured farm timezone. Do not leave it implicit.

**Warning signs:** Late-evening eggs appear under "tomorrow" or charts disagree with what the user saw on the same local day.

## Code Examples

Verified patterns from official sources and repo-specific integration needs:

### FastAPI Lifespan for Shared Runtime Resources
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.bridge.bind_loop(asyncio.get_running_loop())
    pump_task = asyncio.create_task(pump_dashboard_events(...))
    try:
        yield
    finally:
        pump_task.cancel()


app = FastAPI(lifespan=lifespan)
```
Source: https://fastapi.tiangolo.com/advanced/events/

### FastAPI Static Mount
```python
from fastapi.staticfiles import StaticFiles

app.mount("/static", StaticFiles(directory=static_dir), name="static")
```
Source: https://fastapi.tiangolo.com/tutorial/static-files/

### WebSocket Endpoint and Broadcast Shape
```python
from fastapi import WebSocket, WebSocketDisconnect


class ConnectionManager:
    def __init__(self) -> None:
        self.connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        self.connections.discard(websocket)

    async def broadcast(self, payload: dict) -> None:
        stale = []
        for websocket in self.connections:
            try:
                await websocket.send_json(payload)
            except Exception:
                stale.append(websocket)
        for websocket in stale:
            await self.disconnect(websocket)


@app.websocket("/ws")
async def dashboard_ws(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        async for _ in websocket.iter_text():
            pass
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
```
Source: https://www.starlette.io/websockets/

### WebSocket Test Pattern
```python
from fastapi.testclient import TestClient


def test_dashboard_ws_receives_new_egg(app):
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as websocket:
            publish_test_event({"type": "egg_detected", "size": "large"})
            assert websocket.receive_json()["type"] == "egg_detected"
```
Source: https://fastapi.tiangolo.com/advanced/testing-websockets/

### Responsive Chart Container Pattern
```html
<div class="chart-card">
  <div class="chart-shell">
    <canvas id="production-chart"></canvas>
  </div>
</div>
```

```css
.chart-shell {
  position: relative;
  min-height: 240px;
}
```

```javascript
new Chart(canvas, {
  type: "line",
  data,
  options: {
    responsive: true,
    maintainAspectRatio: false,
  },
});
```
Source: https://www.chartjs.org/docs/latest/configuration/responsive.html

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| FastAPI `@app.on_event("startup")` / `shutdown` as the primary lifecycle hook | `FastAPI(lifespan=...)` with an async context manager | Current docs recommend lifespan; startup/shutdown handlers are the older alternative | Use lifespan for queue pumps, pipeline thread startup, and resource cleanup |
| Polling dashboard APIs every second | Native WebSocket push plus API reconciliation | Established modern ASGI/browser pattern | Lower latency and fewer wasted requests |
| CDN-only frontend assets for simple dashboards | Same-origin local assets, optionally vendored | Project-specific best practice for edge/LAN apps | Dashboard still works when internet access is flaky or unavailable |

**Deprecated/outdated:**
- FastAPI startup/shutdown event handlers as the main lifecycle pattern: current docs recommend the `lifespan` parameter instead when managing app-wide startup and cleanup.

## Open Questions

1. **What should happen to tracker auto-collection in web mode?**
   - What we know: the tracker already emits a collection event after all detections disappear, and Phase 3 requires a confirmed dashboard `Collected` action.
   - What's unclear: whether Phase 3 should disable automatic collection entirely, or keep it for non-dashboard CLI mode only.
   - Recommendation: decide in planning that dashboard-confirmed collection is authoritative for Phase 3 and scope any tracker change explicitly.

2. **Should "today" follow UTC or farm-local time?**
   - What we know: timestamps and date fields are currently UTC-based.
   - What's unclear: whether the user expects chart/day buckets to follow local time on the farm.
   - Recommendation: choose explicitly in the plan. If not changing semantics now, document the Phase 3 behavior and avoid silent timezone drift.

3. **How should `Modify Camera` and `Logout` behave in Phase 3?**
   - What we know: the mockup requires the navigation items, but full auth/settings are deferred.
   - What's unclear: whether these should be disabled, informational, or stub endpoints.
   - Recommendation: keep them as explicit stubs/placeholders in Phase 3 and do not let them expand scope.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.4.1 |
| Config file | `pyproject.toml` |
| Quick run command | `pytest -q tests/test_web_api.py tests/test_websocket.py -x` |
| Full suite command | `pytest -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DASH-01 | API returns today's running count by size after considering same-day collection reset | integration | `pytest -q tests/test_web_api.py -k running_summary -x` | NO - Wave 0 |
| DASH-02 | WebSocket client receives `egg_detected` updates within the app runtime | integration | `pytest -q tests/test_websocket.py -k egg_detected -x` | NO - Wave 0 |
| DASH-03 | POST collection endpoint persists collection event and returns/reset state correctly | integration | `pytest -q tests/test_web_api.py -k collected -x` | NO - Wave 0 |
| DASH-04 | Dashboard markup/CSS is usable on a phone-sized viewport | manual-only | `n/a - manual responsive smoke check` | NO - Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest -q tests/test_web_api.py tests/test_websocket.py -x`
- **Per wave merge:** `pytest -q`
- **Phase gate:** Full suite green plus a manual phone-width smoke check before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_web_api.py` - covers DASH-01 and DASH-03
- [ ] `tests/test_websocket.py` - covers DASH-02
- [ ] `tests/test_dashboard_service.py` - covers collection-aware summary logic without ASGI overhead
- [ ] Web dependency install - `pip install fastapi==0.135.1 "uvicorn[standard]==0.41.0" httpx==0.28.1`

## Sources

### Primary (HIGH confidence)
- FastAPI WebSockets docs - https://fastapi.tiangolo.com/advanced/websockets/ - official WebSocket integration pattern
- FastAPI Lifespan Events docs - https://fastapi.tiangolo.com/advanced/events/ - current startup/shutdown guidance
- FastAPI Static Files docs - https://fastapi.tiangolo.com/tutorial/static-files/ - official static asset serving pattern
- FastAPI Testing WebSockets docs - https://fastapi.tiangolo.com/advanced/testing-websockets/ - official WebSocket test pattern
- FastAPI CORS docs - https://fastapi.tiangolo.com/tutorial/cors/ - same-origin vs explicit middleware guidance
- Starlette WebSockets docs - https://www.starlette.io/websockets/ - low-level WebSocket send/receive/iteration behavior
- Starlette TestClient docs - https://www.starlette.io/testclient/ - app-level testing behavior and lifespan context-manager note
- FastAPI PyPI page - https://pypi.org/project/fastapi/ - current version and publish date
- Uvicorn PyPI page - https://pypi.org/project/uvicorn/ - current version, WebSocket support, and `standard` extra
- pytest PyPI page - https://pypi.org/project/pytest/ - current test framework version
- httpx PyPI page - https://pypi.org/project/httpx/ - current version used by TestClient ecosystem
- pytest-asyncio PyPI page - https://pypi.org/project/pytest-asyncio/ - current async test plugin version
- Chart.js Responsive Charts docs - https://www.chartjs.org/docs/latest/configuration/responsive.html - container sizing requirements
- Chart.js Getting Started docs - https://www.chartjs.org/docs/latest/getting-started/ - official integration pattern
- Chart.js GitHub releases - https://github.com/chartjs/Chart.js/releases - current stable release verification

### Secondary (MEDIUM confidence)
- Repo analysis of `src/egg_counter/db.py`, `src/egg_counter/repository.py`, `src/egg_counter/pipeline.py`, and `src/egg_counter/tracker.py` - used to identify collection semantics and runtime integration constraints

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - verified with official docs/releases and tightly aligned to the current repo structure
- Architecture: HIGH - driven by official FastAPI/Starlette patterns plus concrete repo constraints
- Pitfalls: HIGH - based on direct inspection of existing Phase 1/2 code paths and documented Phase 3 decisions

**Research date:** 2026-03-23
**Valid until:** 2026-04-22
