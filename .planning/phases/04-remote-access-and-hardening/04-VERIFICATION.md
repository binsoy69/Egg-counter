---
phase: 04-remote-access-and-hardening
status: human_needed
updated: 2026-03-24T04:16:00Z
requirements:
  - INFRA-01
  - INFRA-02
---

# Phase 4 Verification

## Outcome

Automated and local code checks indicate the phase implementation is structurally complete, but final acceptance still requires Raspberry Pi and public-network validation.

## Verified Automatically

- Auth configuration is environment-driven through [`src/egg_counter/config.py`](D:/codeNcraft/Egg-counter/src/egg_counter/config.py) and non-secret defaults in [`config/settings.yaml`](D:/codeNcraft/Egg-counter/config/settings.yaml).
- Dashboard HTML, JSON API, and websocket endpoints are protected by session auth in [`src/egg_counter/web/server.py`](D:/codeNcraft/Egg-counter/src/egg_counter/web/server.py).
- Login/logout flow and websocket gating were manually exercised with HTTPS and WSS clients against the ASGI app.
- Deployment artifacts exist for dashboard, detector, and tunnel supervision in [`deploy/egg-counter-dashboard.service`](D:/codeNcraft/Egg-counter/deploy/egg-counter-dashboard.service), [`deploy/egg-counter-detector.service`](D:/codeNcraft/Egg-counter/deploy/egg-counter-detector.service), and [`deploy/cloudflared-eggsentry.service`](D:/codeNcraft/Egg-counter/deploy/cloudflared-eggsentry.service).
- The runbook documents install, validation, reboot, and crash-recovery steps in [`docs/remote-access.md`](D:/codeNcraft/Egg-counter/docs/remote-access.md).

## Human Verification Required

1. Deploy the new `deploy/` artifacts and `docs/remote-access.md` procedure on the actual Raspberry Pi target.
2. Confirm the public Cloudflare Tunnel hostname is reachable from cellular data and presents the login page before dashboard content.
3. Confirm successful login from the phone and verify live dashboard access.
4. Reboot or power-cycle the Pi and verify `egg-counter-dashboard`, `egg-counter-detector`, and `cloudflared-eggsentry` restart automatically.
5. Kill the detector service and confirm it returns to `active (running)` within seconds.

## Risks / Gaps

- Local desktop execution cannot prove systemd restart semantics on the Pi.
- Local desktop execution cannot prove Cloudflare DNS/tunnel reachability from a real external network.
- Pytest automation on this machine was blocked by temp-directory permission failures during fixture setup/cleanup, so auth behavior was validated with direct runtime scripts instead.

## Recommendation

Approve Phase 4 after the Pi deployment checklist passes. If any of the hardware or tunnel checks fail, create a gap-closure plan from this verification artifact.
