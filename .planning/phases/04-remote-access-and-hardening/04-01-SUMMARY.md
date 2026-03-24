---
phase: 04-remote-access-and-hardening
plan: 01
subsystem: auth
tags: [fastapi, session, scrypt, websocket, cloudflare]

# Dependency graph
requires:
  - phase: 03-web-dashboard
    provides: FastAPI dashboard routes, WebSocket hub, repository-backed snapshot APIs
provides:
  - Session-based authentication for HTML, API, and websocket access
  - Environment-driven auth configuration and secure cookie settings
  - Mobile login screen for remote dashboard access
  - Route tests for login, logout, unauthorized API access, and websocket gating
affects: [04-remote-access-and-hardening, deploy, docs, websocket]

# Tech tracking
tech-stack:
  added: [starlette-sessionmiddleware]
  patterns: [secure session cookie auth, HTTPS-only test clients, websocket auth gate]

key-files:
  created:
    - src/egg_counter/auth.py
    - src/egg_counter/web/templates/login.html
  modified:
    - config/settings.yaml
    - src/egg_counter/config.py
    - src/egg_counter/web/server.py
    - tests/test_web_api.py
    - tests/test_websocket.py

key-decisions:
  - "Kept auth config environment-driven so secrets stay out of repository YAML"
  - "Used SessionMiddleware with https_only cookies so one session boundary covers HTML, JSON API, and websocket routes"
  - "Validated secure-cookie auth flows with HTTPS and WSS test clients to match production tunnel behavior"

patterns-established:
  - "HTML routes redirect unauthenticated users to /login while API routes return 401 JSON"
  - "Websocket auth rejects before the initial snapshot unless the signed session cookie is present"
  - "Manual auth tests should use https:// and wss:// transports when session cookies are secure"

requirements-completed: [INFRA-01]

# Metrics
duration: 53min
completed: 2026-03-24
---

# Phase 4 Plan 01: Dashboard Authentication Summary

**FastAPI session login protecting dashboard pages, JSON APIs, and websocket feeds with environment-backed credentials**

## Performance

- **Duration:** 53 min
- **Started:** 2026-03-24T03:05:21Z
- **Completed:** 2026-03-24T03:58:00Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Added environment-aware auth settings for username, password hash, session secret, and session max age
- Added `/login` and `/logout`, session middleware, HTML redirects, API `401` responses, and websocket authentication checks
- Added a phone-usable login template and expanded tests for login, logout, unauthorized access, and websocket session enforcement
- Verified the secure-cookie flow manually against HTTPS/WSS transports after pytest was blocked by local temp-directory permission issues

## Task Commits

Inline fallback execution was used after the executor agent stalled before producing a summary artifact.

1. **Task 1: Add environment-aware auth settings and auth helpers** - present in working tree baseline during inline fallback
2. **Task 2: Protect dashboard, API, and websocket routes with login/logout flow** - implemented inline in the current workspace

## Files Created/Modified
- `src/egg_counter/auth.py` - scrypt password hashing, verification, and session helper functions
- `src/egg_counter/web/server.py` - session middleware, login/logout routes, route guards, and websocket auth gate
- `src/egg_counter/web/templates/login.html` - mobile-usable login screen
- `src/egg_counter/config.py` - environment overrides for auth and session settings
- `config/settings.yaml` - non-secret auth defaults
- `tests/test_web_api.py` - auth route coverage and HTTPS test-client handling
- `tests/test_websocket.py` - websocket auth coverage and WSS test-client handling

## Decisions Made
- Kept `/health` unauthenticated for local and tunnel health checks
- Parsed login form data directly from the request body to avoid adding a multipart dependency for a simple form post
- Preserved `https_only=True` in the session middleware and adapted tests to secure transports instead of weakening the cookie policy

## Deviations from Plan

### Auto-fixed Issues

**1. Test transport alignment for secure cookies**
- **Found during:** Task 2 (auth flow verification)
- **Issue:** secure session cookies were not sent on `http://` and `ws://` test transports, causing false auth failures
- **Fix:** shifted auth validations to `https://` and `wss://` clients to mirror the Cloudflare Tunnel production path
- **Files modified:** `tests/test_web_api.py`, `tests/test_websocket.py`
- **Verification:** manual HTTPS and WSS checks passed

---

**Total deviations:** 1 auto-fixed
**Impact on plan:** No scope increase. The adjustment was necessary to validate the intended secure-cookie behavior.

## Issues Encountered
- The `gsd-executor` subagent stalled without creating a summary or returning completion, so execution continued inline.
- Local pytest runs were blocked by temp-directory permission errors on this machine; manual runtime checks were used to verify the auth flows instead.

## User Setup Required
None yet. Operator setup is documented in Plan 02 deployment artifacts.

## Next Phase Readiness
- The dashboard now has an application-managed login boundary suitable for Cloudflare Tunnel exposure
- Deployment artifacts can safely assume the local dashboard origin is authenticated
- Hardware validation is still required later for actual remote URL access and reboot/crash recovery

---
*Phase: 04-remote-access-and-hardening*
*Completed: 2026-03-24*

## Self-Check: PASSED
