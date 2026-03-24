# Phase 4: Remote Access and Hardening - Research

**Researched:** 2026-03-24
**Domain:** Remote HTTPS access, app authentication, and Raspberry Pi service hardening
**Confidence:** HIGH

## Summary

Phase 4 should build on the existing FastAPI dashboard and `egg-counter serve` runtime rather than introducing a new hosting tier. The most direct path is:

1. Keep FastAPI/Uvicorn bound locally on the Pi.
2. Put `cloudflared` in front of that local HTTP service to provide a stable HTTPS URL.
3. Add simple application-level login using a single configured username/password and signed session cookie.
4. Run the dashboard and detection pipeline as separate `systemd` services so each can start on boot and restart independently.

That approach matches the locked decisions in `04-CONTEXT.md`: remote access stays public-but-authenticated, the auth model remains app-managed rather than Cloudflare Access email codes, and boot/crash behavior covers both the dashboard server and the detection pipeline.

**Primary recommendation:** implement app auth inside FastAPI with a password hash and signed session cookie, keep `cloudflared` as a separate service that proxies to the local dashboard, and manage `egg-counter run`, `egg-counter serve`, and `cloudflared` with explicit `systemd` unit files plus an environment file for secrets and paths.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Remote access must be internet-reachable, but not anonymously open. The dashboard should be exposed publicly over HTTPS and protected by a login flow.
- **D-02:** The user does not have an existing domain. Phase 4 may use a Cloudflare-managed or newly created hostname rather than requiring a user-owned domain before implementation can proceed.
- **D-03:** Local-network fallback is acceptable if it naturally remains available, but it is not required by the phase success criteria. Remote access is the primary goal.
- **D-04:** Authentication should be handled by the application itself using a basic username/password model, not Cloudflare Access one-time email codes.
- **D-05:** Single-user access remains the assumption. No self-registration, multi-user management, or OAuth flows are needed.
- **D-06:** Login protection applies to the remote dashboard experience; the implementation may choose the exact session/cookie mechanics.
- **D-07:** After a Raspberry Pi reboot or power cycle, both the detection process and the dashboard server must come back automatically with no manual steps.
- **D-08:** If the detection process crashes repeatedly, the system should continue attempting automatic restarts rather than stopping after a limited retry count.
- **D-09:** This phase should feel hands-off in day-to-day use. The intended steady state is that the user only opens the dashboard from a phone and does not routinely SSH into the Pi for normal operation.
- **D-10:** Reliability work should cover the full runtime needed for the product: the web dashboard and the live detection pipeline, not just one of them.
- **D-11:** Claude may decide whether that is best implemented as one service process or multiple coordinated services, as long as the reboot and crash-recovery behavior stays simple and reliable for a single-user Pi deployment.

### Claude's Discretion
- Exact auth implementation details (session middleware, password storage approach, login route shape)
- Exact Cloudflare Tunnel setup mechanics and whether a locally reachable URL continues to be documented/supported
- systemd unit structure, restart settings, dependency ordering, and environment-file layout
- Log routing strategy for production operation
- Whether health checks or small helper scripts are needed to keep the service model maintainable

### Deferred Ideas (OUT OF SCOPE)
- Rich admin settings UI for managing deployment, tunnel, or auth from the browser
- Multi-user roles, password reset flows, or external identity providers
- Advanced observability/alerting beyond what is needed for restartable Pi services
- Making LAN fallback a formal requirement
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INFRA-01 | Dashboard is accessible remotely from phone via Cloudflare Tunnel | Keep FastAPI local, add `cloudflared` tunnel config, expose stable HTTPS hostname, and protect app routes with login/session middleware. |
| INFRA-02 | System auto-starts on Pi boot and auto-restarts on crash | Use dedicated `systemd` units for detector, dashboard, and `cloudflared`, with `Restart=always`, `RestartSec`, and `WantedBy=multi-user.target`. |
</phase_requirements>

## Standard Stack

### Core
| Library / Tool | Purpose | Why Standard |
|----------------|---------|--------------|
| FastAPI + current web server | Existing dashboard runtime | Already implemented in repo and already serves `/health`, API routes, and WebSocket endpoints. |
| `cloudflared` | HTTPS ingress to the Pi | Directly satisfies Cloudflare Tunnel requirement without opening router ports. |
| `systemd` | Service supervision on Raspberry Pi OS | Native process management for boot start, crash restart, dependency ordering, and journald logs. |

### Supporting
| Library | Purpose | When to Use |
|---------|---------|-------------|
| `itsdangerous` or Starlette/FastAPI session middleware | Signed cookie session | If current dependency set needs a lightweight cookie/session primitive. |
| `hashlib.scrypt` or `bcrypt`/`passlib` | Password verification | Prefer a secure hash check over storing plaintext credentials. |
| `.env` / `EnvironmentFile=` | Secret injection | For username, password hash, session secret, tunnel token/config path, and model path. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| App-level username/password | Cloudflare Access email OTP | Conflicts with locked decision D-04. |
| Separate reverse proxy (nginx/Caddy) | Keep only Uvicorn + `cloudflared` | Reverse proxy is unnecessary extra moving parts for a single-user Pi deployment. |
| One giant service script | Separate dashboard and detector services | One process tree is simpler to start but harder to restart selectively and harder to debug. |

## Repo-State Findings

### Existing assets to reuse
- `src/egg_counter/cli.py` already has `run` and `serve` entrypoints, so Phase 4 can supervise those directly.
- `src/egg_counter/web/server.py` already exposes `/health`, dashboard routes, and WebSocket endpoints.
- `src/egg_counter/pipeline.py` already cleanly manages the long-running detector runtime.
- `config/settings.yaml` already contains `web_host`, `web_port`, `collection_mode`, and `db_path`.

### Current gaps Phase 4 must close
- No login/session enforcement exists in the FastAPI app.
- No password/secret configuration surface exists.
- No deployment documentation or runtime service files exist for `cloudflared` or `systemd`.
- No tests currently exercise authenticated-vs-unauthenticated dashboard access.
- No production verification path currently proves boot recovery, crash restart, or remote phone access.

## Architecture Patterns

### Pattern 1: App-Managed Session Login
**What:** Add a `/login` form/JSON handler, a password verification helper, and session/cookie enforcement for HTML, API, and WebSocket access.
**When to use:** This is the main auth model for the remote dashboard.

Recommended shape:
- Add config/env values for `auth_username`, `auth_password_hash`, and `session_secret`.
- Verify password on login using a hashed comparison.
- Set an `HttpOnly`, `Secure`, `SameSite=Lax` cookie.
- Require auth on `/`, `/dashboard`, `/history`, `/api/*`, and `/ws`.
- Allow `/health` to remain unauthenticated for local/tunnel checks.

### Pattern 2: Local HTTP + Cloudflare Tunnel
**What:** Keep Uvicorn bound to `127.0.0.1` or LAN as needed, and have `cloudflared` route a public hostname to `http://127.0.0.1:8000`.
**When to use:** For all remote access in this phase.

Recommended tunnel config:
- Named tunnel with config file on the Pi.
- Public hostname mapping to the dashboard service.
- Local origin should be plain HTTP on loopback; Cloudflare handles public TLS termination.
- WebSockets are supported through the same tunnel path, so the existing live dashboard can remain in-process.

### Pattern 3: Split Services with Shared Environment File
**What:** Create separate `systemd` units:
- `egg-counter-detector.service`
- `egg-counter-dashboard.service`
- `cloudflared.service` or project-specific tunnel service

**When to use:** This is the recommended production topology.

Why split:
- Detector crash should not bring down the dashboard.
- Dashboard restart should not disrupt detector counting.
- Each service can have its own `ExecStart`, restart policy, and logs.

### Pattern 4: Boot and Crash Recovery via `systemd`
**What:** Use `Restart=always`, `RestartSec=5`, working directory, environment file, and `After=network-online.target`.
**When to use:** Required for INFRA-02.

Recommended `systemd` traits:
- `Type=simple`
- `Restart=always`
- `RestartSec=5`
- `WorkingDirectory=/opt/egg-counter` or repo checkout path
- `EnvironmentFile=/etc/egg-counter/egg-counter.env`
- `WantedBy=multi-user.target`

## Recommended Project Structure

```
config/
  settings.yaml                 # add auth/deployment defaults only if non-secret

deploy/
  egg-counter-dashboard.service
  egg-counter-detector.service
  cloudflared-eggsentry.service
  cloudflared-config.yml
  egg-counter.env.example

src/egg_counter/
  auth.py                       # password verification + session helpers
  web/server.py                 # login/logout routes + auth enforcement

tests/
  test_auth.py
  test_web_api.py               # auth coverage additions
```

## Auth Design (Claude's Discretion)

### Recommended approach
- Store secrets outside `settings.yaml`; use environment variables loaded by service files.
- Keep exactly one configured username.
- Store only a password hash, not plaintext.
- Add login and logout routes.
- Use a signed cookie session with explicit TTL.

### Concrete recommendations
- `EGG_COUNTER_AUTH_USERNAME`
- `EGG_COUNTER_AUTH_PASSWORD_HASH`
- `EGG_COUNTER_SESSION_SECRET`
- optional `EGG_COUNTER_SESSION_MAX_AGE=1209600` (14 days)

### Route behavior
- Unauthenticated HTML route requests redirect to `/login`.
- Unauthenticated API requests return `401`.
- Unauthenticated WebSocket requests reject the handshake or close immediately with policy violation.
- `/health` stays open.

## systemd Design

### Detector service
Use `egg-counter run --model ... --config ... --zone ...`

Responsibilities:
- Boot-start camera/detection pipeline
- Auto-restart after crash
- Continue running even if dashboard is unavailable

### Dashboard service
Use `egg-counter serve --config ... --zone ... --host 127.0.0.1 --port 8000`

Responsibilities:
- Serve local dashboard/API/WebSocket runtime
- Enforce app auth
- Provide local health check for tunnel validation

### Tunnel service
Use `cloudflared tunnel run <name>` or the installed service wrapper

Responsibilities:
- Expose stable HTTPS hostname
- Start after network
- Reconnect automatically after connectivity loss

## Cloudflare Tunnel Notes

### Recommended operational shape
- Use a Cloudflare-managed hostname if no owned domain is available yet.
- Document one stable public URL for phone bookmarks.
- Keep origin on the Pi; do not proxy to a second machine.

### Required planner considerations
- How the initial tunnel is provisioned and where credentials live.
- Whether install/setup is fully scripted or partly documented manual steps.
- How to verify WebSocket traffic over the tunnel.
- How to keep remote access working across Pi reboot without re-authenticating the tunnel locally.

## Common Pitfalls

### Pitfall 1: Storing plaintext password in repo config
**What goes wrong:** Auth credentials end up committed or readable to anyone with repo access.
**How to avoid:** Keep only env-driven secrets or password hashes in `/etc/egg-counter/egg-counter.env`.

### Pitfall 2: Protecting HTML routes but leaving APIs/WebSockets open
**What goes wrong:** A remote user can bypass the login page by calling JSON or WebSocket endpoints directly.
**How to avoid:** Apply the same auth check to `/api/*` and `/ws`.

### Pitfall 3: Running `cloudflared` inside the app process
**What goes wrong:** Tunnel restarts and dashboard restarts become coupled.
**How to avoid:** Separate `systemd` service for `cloudflared`.

### Pitfall 4: Binding dashboard only to LAN without tunnel origin alignment
**What goes wrong:** Tunnel points to the wrong interface/port or fails after boot because the origin is not reachable.
**How to avoid:** Standardize dashboard origin to `127.0.0.1:8000` for tunnel use and document any LAN fallback deliberately.

### Pitfall 5: Restart loops without observability
**What goes wrong:** A bad config causes endless restarts with no actionable logs.
**How to avoid:** Use journald logs, clear `ExecStart`, and document `journalctl -u <service>` verification commands.

## Rollout Strategy

1. Add auth module and session enforcement with tests.
2. Add env/config loading for auth secrets.
3. Add deployment artifacts: env example, service files, tunnel config/example, setup docs.
4. Add smoke-test/documented verification steps for local auth, local health, tunnel route, reboot, and crash restart.
5. Validate on Pi hardware with manual reboot and forced-process-kill checks.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `pyproject.toml` |
| Quick run command | `python -m pytest tests/test_web_api.py tests/test_websocket.py tests/test_pipeline.py -x -q` |
| Full suite command | `python -m pytest tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-01a | Unauthenticated dashboard/API access is blocked | unit/integration | `python -m pytest tests/test_web_api.py -k auth -x -q` | Wave 0 |
| INFRA-01b | Valid login establishes session and allows dashboard/API access | integration | `python -m pytest tests/test_web_api.py -k login -x -q` | Wave 0 |
| INFRA-01c | WebSocket requires authenticated session | integration | `python -m pytest tests/test_websocket.py -k auth -x -q` | Wave 0 |
| INFRA-01d | Deployment artifacts include Cloudflare tunnel config/instructions | static | `rg -n "cloudflared|tunnel" deploy .planning` | Wave 1 |
| INFRA-02a | Dashboard service files exist with restart policy | static | `rg -n "Restart=always|WantedBy=multi-user.target|ExecStart=" deploy\\*.service deploy\\**\\*.service` | Wave 1 |
| INFRA-02b | Detector service files exist with restart policy | static | `rg -n "egg-counter run|Restart=always" deploy\\*.service deploy\\**\\*.service` | Wave 1 |
| INFRA-02c | Manual reboot recovery verified on Pi | manual | `sudo reboot` + post-boot checks | Manual |
| INFRA-02d | Manual crash recovery verified on Pi | manual | `pkill -f "egg-counter run"` + `systemctl status` | Manual |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_web_api.py tests/test_websocket.py tests/test_pipeline.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -x -q`
- **Phase gate:** automated suite plus Pi manual checks for reboot, restart, and remote phone access

### Wave 0 Gaps
- [ ] `tests/test_auth.py` or equivalent auth cases added to existing web tests
- [ ] Auth coverage added for HTML, API, and WebSocket paths
- [ ] `deploy/*.service` files added
- [ ] `deploy/egg-counter.env.example` added
- [ ] `deploy/cloudflared-config.yml` or equivalent example added

## Manual Verification Requirements

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Phone on cellular can load the dashboard over HTTPS | INFRA-01 | Requires real remote network path | Disable Wi-Fi on phone, open tunnel URL, confirm login page then dashboard after auth |
| Dashboard and detector start after Pi reboot | INFRA-02 | Requires actual boot cycle | Reboot Pi, wait for boot, run `systemctl status` on services and load dashboard remotely |
| Detector restarts after crash within seconds | INFRA-02 | Requires service manager on target hardware | Kill detector process, confirm `systemd` restarts it and logs show recovery |

## Environment Availability

| Dependency | Required By | Available | Notes |
|------------|-------------|-----------|-------|
| Python / FastAPI / Uvicorn | Dashboard service | Yes | Already present in repo dependencies |
| `cloudflared` | Remote ingress | Unknown in repo | Likely host-installed on Pi, not a Python dependency |
| `systemd` | Boot and restart supervision | Expected on Raspberry Pi OS | Host capability, not a repo dependency |

**Missing dependencies with fallback:** `cloudflared` is not part of Python deps and should be treated as host install/config work.

## Sources

### Primary (HIGH confidence)
- Existing codebase: `src/egg_counter/cli.py`, `src/egg_counter/pipeline.py`, `src/egg_counter/web/server.py`, `config/settings.yaml`
- Existing phase context: `04-CONTEXT.md`, `03-CONTEXT.md`, `02-CONTEXT.md`
- FastAPI/Starlette session/cookie patterns and `systemd` service conventions

### Secondary (MEDIUM confidence)
- Cloudflare Tunnel operational norms for local HTTP origins and persistent named tunnels
- Raspberry Pi service deployment practices using `systemd` and journald

## Metadata

**Confidence breakdown:**
- Stack choice: HIGH
- Auth/session pattern: HIGH
- Tunnel/service topology: HIGH
- Final Pi-specific rollout details: MEDIUM until validated on target hardware

**Research date:** 2026-03-24
**Valid until:** 2026-04-24
