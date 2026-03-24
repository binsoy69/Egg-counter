---
phase: 4
slug: remote-access-and-hardening
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-24
---

# Phase 4 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `python -m pytest tests/test_web_api.py tests/test_websocket.py tests/test_pipeline.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~20 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_web_api.py tests/test_websocket.py tests/test_pipeline.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -x -q`
- **Before `$gsd-verify-work`:** Full suite must be green plus manual Pi checks complete
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | INFRA-01 | integration | `python -m pytest tests/test_web_api.py -k auth -x -q` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | INFRA-01 | integration | `python -m pytest tests/test_websocket.py -k auth -x -q` | ❌ W0 | ⬜ pending |
| 04-01-03 | 01 | 1 | INFRA-02 | static | `rg -n "Restart=always|WantedBy=multi-user.target|ExecStart=" deploy` | ❌ W0 | ⬜ pending |
| 04-01-04 | 01 | 1 | INFRA-01 | static | `rg -n "cloudflared|tunnel" deploy .planning` | ❌ W0 | ⬜ pending |
| 04-01-05 | 01 | 2 | INFRA-02 | manual | `systemctl status egg-counter-dashboard egg-counter-detector` | ❌ manual | ⬜ pending |
| 04-01-06 | 01 | 2 | INFRA-01 | manual | Phone cellular smoke test against tunnel URL | ❌ manual | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_web_api.py` - auth/login/logout access checks
- [ ] `tests/test_websocket.py` - authenticated-vs-unauthenticated websocket checks
- [ ] `deploy/egg-counter-dashboard.service` - supervised dashboard runtime
- [ ] `deploy/egg-counter-detector.service` - supervised detector runtime
- [ ] `deploy/cloudflared-config.yml` or equivalent tunnel config/example
- [ ] `deploy/egg-counter.env.example` - non-secret env contract for deployment

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Remote HTTPS dashboard reachable from cellular | INFRA-01 | Requires real remote network path and phone | Disable phone Wi-Fi, open tunnel URL, verify login page and post-login dashboard load |
| Services recover after Pi reboot | INFRA-02 | Requires actual target hardware reboot | Reboot Pi, wait for boot, verify `egg-counter-dashboard`, `egg-counter-detector`, and tunnel service are active |
| Detector process restarts after crash | INFRA-02 | Requires live `systemd` supervision | Kill detector process, confirm service restarts within seconds via `systemctl status` and `journalctl` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
