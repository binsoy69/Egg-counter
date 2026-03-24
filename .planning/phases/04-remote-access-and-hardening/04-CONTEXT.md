# Phase 4: Remote Access and Hardening - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver secure remote phone access to the existing dashboard over HTTPS and make the system production-reliable on the Raspberry Pi. This phase covers Cloudflare Tunnel-based exposure, app login protection, and service management so the detection process and web server start automatically on boot and restart automatically after crashes.

</domain>

<decisions>
## Implementation Decisions

### Remote Access Model
- **D-01:** Remote access must be internet-reachable, but not anonymously open. The dashboard should be exposed publicly over HTTPS and protected by a login flow.
- **D-02:** The user does not have an existing domain. Phase 4 may use a Cloudflare-managed or newly created hostname rather than requiring a user-owned domain before implementation can proceed.
- **D-03:** Local-network fallback is acceptable if it naturally remains available, but it is not required by the phase success criteria. Remote access is the primary goal.

### Authentication
- **D-04:** Authentication should be handled by the application itself using a basic username/password model, not Cloudflare Access one-time email codes.
- **D-05:** Single-user access remains the assumption. No self-registration, multi-user management, or OAuth flows are needed.
- **D-06:** Login protection applies to the remote dashboard experience; the implementation may choose the exact session/cookie mechanics.

### Boot and Crash Recovery
- **D-07:** After a Raspberry Pi reboot or power cycle, both the detection process and the dashboard server must come back automatically with no manual steps.
- **D-08:** If the detection process crashes repeatedly, the system should continue attempting automatic restarts rather than stopping after a limited retry count.
- **D-09:** This phase should feel hands-off in day-to-day use. The intended steady state is that the user only opens the dashboard from a phone and does not routinely SSH into the Pi for normal operation.

### Service Topology
- **D-10:** Reliability work should cover the full runtime needed for the product: the web dashboard and the live detection pipeline, not just one of them.
- **D-11:** Claude may decide whether that is best implemented as one service process or multiple coordinated services, as long as the reboot and crash-recovery behavior stays simple and reliable for a single-user Pi deployment.

### Claude's Discretion
- Exact auth implementation details (session middleware, password storage approach, login route shape)
- Exact Cloudflare Tunnel setup mechanics and whether a locally reachable URL continues to be documented/supported
- systemd unit structure, restart settings, dependency ordering, and environment-file layout
- Log routing strategy for production operation
- Whether health checks or small helper scripts are needed to keep the service model maintainable

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase requirements
- `.planning/ROADMAP.md` - Phase 4 goal, success criteria, and dependency on Phase 3
- `.planning/REQUIREMENTS.md` - INFRA-01 and INFRA-02 define the infrastructure requirements for this phase
- `.planning/PROJECT.md` - remote phone access is the remaining active v1 requirement; single-user scope remains in force

### Prior phase decisions
- `.planning/phases/03-web-dashboard/03-CONTEXT.md` - dashboard is local-network in Phase 3; remote access is explicitly deferred to Phase 4
- `.planning/phases/02-data-persistence/02-CONTEXT.md` - SQLite on the Pi SD card remains the persistence layer the services must run against
- `.planning/STATE.md` - current project state and open hardware verification concerns

### Existing implementation
- `src/egg_counter/cli.py` - current runtime entrypoints for `run` and `serve`
- `src/egg_counter/pipeline.py` - long-running detection process that needs managed startup and restart behavior
- `src/egg_counter/web/server.py` - FastAPI app, health route, and dashboard/websocket endpoints that will sit behind remote access
- `config/settings.yaml` - existing runtime configuration surface for host/port and app settings
- `pyproject.toml` - current packaged dependencies and script entrypoint

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/egg_counter/cli.py` already separates detection (`run`) from dashboard serving (`serve`), giving Phase 4 clear service entrypoints.
- `src/egg_counter/web/server.py` already provides `/health`, which can support operational checks and tunnel validation.
- `config/settings.yaml` already carries web host/port settings and can be extended for auth or deployment configuration if needed.

### Established Patterns
- The project is a Python monolith with FastAPI for the web layer and a long-running OpenCV/YOLO pipeline for detection.
- SQLite on local disk is the source of truth, so the hardened deployment should assume local file access on the Pi.
- The dashboard already assumes single-user usage from a phone, which aligns with a simple auth model.

### Integration Points
- Production startup likely needs to invoke one or both existing CLI commands under service supervision.
- App-level login will need to integrate into the FastAPI server without breaking the existing dashboard, history, API, and websocket flows.
- Cloudflare Tunnel should front the existing FastAPI HTTP service rather than introducing a separate externally hosted application tier.

</code_context>

<specifics>
## Specific Ideas

- The remote URL should be simple enough for routine phone use and stable enough that the user can bookmark it.
- Security should be proportionate to a single-user farm utility app: straightforward login protection, not enterprise identity management.
- Reliability should bias toward automatic recovery and minimal operator involvement.

</specifics>

<deferred>
## Deferred Ideas

- Rich admin settings UI for managing deployment, tunnel, or auth from the browser
- Multi-user roles, password reset flows, or external identity providers
- Advanced observability/alerting beyond what is needed for restartable Pi services
- Making LAN fallback a formal requirement; it may exist, but remote access is the only required access path in this phase

</deferred>

---

*Phase: 04-remote-access-and-hardening*
*Context gathered: 2026-03-24*
