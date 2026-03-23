# Phase 3: Web Dashboard - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver a mobile-first web dashboard, usable on both phone and larger screens, that shows today's running egg count by size, updates live when new eggs are detected, lets the user mark eggs as collected, and shows historical production trends. The dashboard runs on the local network in this phase. Remote internet access is handled in Phase 4.

</domain>

<decisions>
## Implementation Decisions

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

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase requirements
- `.planning/ROADMAP.md` - Phase 3 goal, success criteria, and dependency on Phase 2
- `.planning/REQUIREMENTS.md` - DASH-01, DASH-02, DASH-03, and DASH-04 define the dashboard requirements for this phase
- `.planning/PROJECT.md` - Product scope, mobile phone usage context, WebSocket requirement, and out-of-scope constraints

### Prior phase decisions
- `.planning/phases/01-detection-pipeline/01-CONTEXT.md` - collection is an all-at-once action and Phase 3 owns the dashboard-side collection/reset flow
- `.planning/phases/02-data-persistence/02-CONTEXT.md` - `EggRepository` is the intended query interface that Phase 3 should consume

### UI mockups
- `ui_mockups/dashboard_upper_half.png` - dashboard top-half layout, navigation, camera summary row, period summary cards, and KPI cards
- `ui_mockups/dashboard_lower_half.png` - dashboard chart layout and visual hierarchy
- `ui_mockups/history.png` - history page layout, filters, and records table/list structure

### Architecture and stack guidance
- `.planning/research/ARCHITECTURE.md` - recommended web-server/dashboard structure for this project, including static dashboard delivery and FastAPI WebSocket integration
- `.planning/research/STACK.md` - recommended Phase 3 stack choices: FastAPI, native WebSocket, vanilla HTML/CSS/JS, and Chart.js

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/egg_counter/repository.py`: provides `get_daily_summary()`, `get_eggs_by_date_range()`, and `get_size_breakdown()` for dashboard and history data
- `src/egg_counter/db.py`: owns the SQLite schema and collection-event persistence that dashboard actions must update consistently
- `src/egg_counter/pipeline.py`: current runtime source of new egg and collection events; future web layer must integrate with this live event flow
- `tests/test_repository.py`: existing coverage for repository query shapes that the dashboard API can rely on

### Established Patterns
- Python monolith structure under `src/egg_counter/`; no frontend stack or web server exists yet
- SQLite is the single source of truth for historical data
- UTC timestamps and date fields are the established persistence pattern
- Configuration already flows through `config/settings.yaml` and `load_settings()`

### Integration Points
- Phase 3 should read historical/count data through `EggRepository` rather than adding ad hoc SQL in the UI layer
- The live dashboard update path must connect runtime egg events from the pipeline/logger side to a browser-facing WebSocket stream
- Collection actions in the dashboard must map back to the same persisted collection-event model already used by `EggDatabaseLogger`

</code_context>

<specifics>
## Specific Ideas

- The dashboard should feel like the supplied mockups, not a generic admin panel.
- The implementation should be mobile-first but still work cleanly on larger screens.
- New egg events should be noticeable without being noisy: immediate data refresh plus a short-lived toast.
- The history page should remain simple in Phase 3: the mockup filters and newest-first ordering are enough.

</specifics>

<deferred>
## Deferred Ideas

- Predefined username/password authentication with no self-registration - separate capability, not required by the current Phase 3 roadmap entry
- `Modify Camera` as a full settings flow for cage count / chickens-per-cage changes - separate capability from the current Phase 3 success criteria; may be informational or stubbed unless explicitly added to roadmap

</deferred>

---

*Phase: 03-web-dashboard*
*Context gathered: 2026-03-23*
