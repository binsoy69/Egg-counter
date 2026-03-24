# Remote Access Runbook

This runbook assumes the repo is deployed at `/opt/egg-counter` on the Raspberry Pi and that the authenticated dashboard from Phase 4 is being exposed through Cloudflare Tunnel.

## Install and enable services

1. Copy the repo to `/opt/egg-counter` and install the `egg-counter` package into the runtime environment used by the services.
2. Copy the unit files from `deploy/` into `/etc/systemd/system/`.
3. Copy `deploy/egg-counter.env.example` to `/etc/egg-counter/egg-counter.env` and replace the placeholder values.
4. Reload systemd and enable the services:

```bash
sudo systemctl daemon-reload
sudo systemctl enable egg-counter-dashboard egg-counter-detector cloudflared-eggsentry
sudo systemctl start egg-counter-dashboard egg-counter-detector cloudflared-eggsentry
sudo systemctl status egg-counter-dashboard egg-counter-detector cloudflared-eggsentry
```

## Configure auth secrets

Set these values in `/etc/egg-counter/egg-counter.env`:

- `EGG_COUNTER_MODEL_PATH=/opt/egg-counter/models/egg-model`
- `EGG_COUNTER_AUTH_USERNAME=<dashboard-login-user>`
- `EGG_COUNTER_AUTH_PASSWORD_HASH=<scrypt$... hash>`
- `EGG_COUNTER_SESSION_SECRET=<long-random-secret>`
- `EGG_COUNTER_SESSION_MAX_AGE=1209600`

Keep `config/settings.yaml` free of plaintext credentials. The app reads the auth values from the environment at process start.

## Configure Cloudflare Tunnel

1. Install `cloudflared` on the Pi.
2. Authenticate and create a tunnel named `eggsentry`.
3. Place the tunnel credential JSON at `/etc/cloudflared/eggsentry.json`.
4. Update `deploy/cloudflared-config.yml` with the real hostname that should point to the dashboard.
5. Copy the tunnel config to `/opt/egg-counter/deploy/cloudflared-config.yml`.
6. Start or restart the tunnel service after any config change.

The tunnel origin must remain `http://127.0.0.1:8000` so the public edge only reaches the locally bound authenticated dashboard service.

## Validation

Run these checks after deployment:

```bash
curl http://127.0.0.1:8000/health
sudo systemctl status egg-counter-dashboard egg-counter-detector cloudflared-eggsentry
journalctl -u egg-counter-detector -n 100 --no-pager
```

Then validate from a phone on cellular data:

1. Open the configured HTTPS hostname.
2. Confirm the login page appears before any dashboard content.
3. Sign in with the configured credentials.
4. Confirm the dashboard loads and live updates still arrive.

## Reboot test

1. Trigger a reboot: `sudo reboot`
2. After the Pi comes back, run:

```bash
sudo systemctl status egg-counter-dashboard egg-counter-detector cloudflared-eggsentry
curl http://127.0.0.1:8000/health
```

3. Confirm all three services are active without manual restarts.
4. Confirm the public HTTPS URL is reachable again and still requires login.

## Crash recovery test

1. Simulate a detector crash:

```bash
sudo systemctl kill egg-counter-detector
sleep 10
sudo systemctl status egg-counter-detector
journalctl -u egg-counter-detector -n 100 --no-pager
```

2. Confirm `egg-counter-detector` returns to `active (running)` automatically within a few seconds.
3. Repeat the same pattern for `egg-counter-dashboard` and `cloudflared-eggsentry` if you need to verify each restart policy independently.
