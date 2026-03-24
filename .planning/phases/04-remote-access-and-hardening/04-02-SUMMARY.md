---
phase: 04-remote-access-and-hardening
plan: 02
subsystem: infra
tags: [systemd, cloudflared, deployment, raspberry-pi, operations]

# Dependency graph
requires:
  - phase: 04-remote-access-and-hardening
    provides: Authenticated FastAPI dashboard on localhost:8000
provides:
  - systemd units for dashboard, detector, and Cloudflare Tunnel
  - Example environment contract for model path and auth secrets
  - Cloudflare Tunnel example configuration targeting localhost dashboard origin
  - Operator runbook for installation, validation, reboot, and crash-recovery checks
affects: [deployment, operations, cloudflare, raspberry-pi]

# Tech tracking
tech-stack:
  added: [systemd, cloudflared]
  patterns: [split-service supervision, env-file deployment contract, runbook-based verification]

key-files:
  created:
    - deploy/egg-counter-dashboard.service
    - deploy/egg-counter-detector.service
    - deploy/cloudflared-eggsentry.service
    - deploy/cloudflared-config.yml
    - deploy/egg-counter.env.example
    - docs/remote-access.md
  modified: []

key-decisions:
  - "Kept the dashboard service bound to 127.0.0.1 because Cloudflare Tunnel should be the public entry point"
  - "Split dashboard, detector, and tunnel into separate supervised services so each can restart independently"
  - "Documented reboot and crash-recovery checks explicitly because those requirements cannot be proven from local desktop execution"

patterns-established:
  - "Use /etc/egg-counter/egg-counter.env as the deployment secret contract"
  - "Bind the dashboard locally and publish it through cloudflared ingress rather than direct public exposure"
  - "Treat Pi reboot and process-crash checks as runbook-driven acceptance tests"

requirements-completed: [INFRA-01, INFRA-02]

# Metrics
duration: 18min
completed: 2026-03-24
---

# Phase 4 Plan 02: Remote Access Deployment Summary

**systemd-managed dashboard, detector, and Cloudflare Tunnel deployment artifacts with a concrete Pi operations runbook**

## Performance

- **Duration:** 18 min
- **Started:** 2026-03-24T03:58:00Z
- **Completed:** 2026-03-24T04:16:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Added systemd unit files for independently supervised dashboard, detector, and cloudflared services
- Added an environment example file covering model path, auth username, auth password hash, session secret, and session max age
- Added a Cloudflare Tunnel example config pointing HTTPS traffic to `http://127.0.0.1:8000`
- Added an operator runbook covering installation, service enable/start commands, validation, reboot tests, and crash recovery tests

## Task Commits

Inline execution continued in the current workspace after the executor-agent path was abandoned.

1. **Task 1: Add concrete systemd unit files and environment contract for Pi deployment** - implemented inline in the current workspace
2. **Task 2: Add Cloudflare Tunnel example config and operator runbook for remote validation** - implemented inline in the current workspace

## Files Created/Modified
- `deploy/egg-counter-dashboard.service` - systemd unit for the local-only FastAPI dashboard
- `deploy/egg-counter-detector.service` - detector runtime with restart policy and model-path environment variable
- `deploy/cloudflared-eggsentry.service` - Cloudflare Tunnel systemd unit tied to dashboard availability
- `deploy/cloudflared-config.yml` - tunnel example routing HTTPS traffic to localhost dashboard origin
- `deploy/egg-counter.env.example` - secret/runtime environment contract
- `docs/remote-access.md` - install, enable, validate, reboot, and crash-recovery runbook

## Decisions Made
- Kept the dashboard bound to loopback so Cloudflare Tunnel is the sole remote ingress
- Used separate services to avoid coupling detector restarts to dashboard or tunnel restarts
- Documented validation as operator actions rather than claiming local proof for Pi-specific reboot and crash behavior

## Deviations from Plan

None - plan executed as specified.

## Issues Encountered
- No code-level blockers. This plan was artifact-heavy and verified primarily through exact content checks rather than runtime execution on the current machine.

## User Setup Required
Manual Pi setup is required:
- copy the service files into `/etc/systemd/system/`
- populate `/etc/egg-counter/egg-counter.env`
- install and authenticate `cloudflared`
- run the validation, reboot, and crash-recovery checks from `docs/remote-access.md`

## Next Phase Readiness
- The project now has concrete deployment artifacts for remote access on Raspberry Pi hardware
- Remaining proof for Phase 4 depends on human validation of the deployed Pi and cellular-access URL

---
*Phase: 04-remote-access-and-hardening*
*Completed: 2026-03-24*

## Self-Check: PASSED
