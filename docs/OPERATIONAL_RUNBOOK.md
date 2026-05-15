# Operational Runbook (MVP)

## Scope
This runbook covers local-first Docker operation for `tax-return-ai` on Raspberry Pi.

## Start/Stop
- Start: `make up`
- Stop: `make down`
- Logs: `make logs`
- Render compose config: `docker compose config`

## Health Checks
- Backend health: `curl -sS http://127.0.0.1:8020/api/health`
- Frontend header check: `curl -sSI http://127.0.0.1:3030`
- In-container status: `docker compose ps`

## Data Locations
- SQLite DB: `data/taxapp.db`
- Uploaded files: `data/uploads/`
- Encrypted review packs: `data/exports/`
- Environment file: `.env`

## Backup (Manual)
1. Stop writes (recommended): `make down`
2. Archive data: `tar -czf backup-$(date +%F-%H%M).tar.gz data .env`
3. Store backup in secure offline location.
4. Restart: `make up`

## Restore (Manual)
1. Stop app: `make down`
2. Restore archive into project root.
3. Ensure file ownership/permissions are correct for Docker user.
4. Start app: `make up`
5. Validate: `curl -sS http://127.0.0.1:8020/api/health`

## Cloudflare Tunnel Checks
- Verify tunnel config points to the new local ports for this build:
  - `taxai.signpega.com -> http://127.0.0.1:3030`
  - `taxai-api.signpega.com -> http://127.0.0.1:8020`
- Service status (host): `sudo systemctl status cloudflared`
- Recent logs: `journalctl -u cloudflared -n 200 --no-pager`

## Secret Rotation
- Rotate `.env` secrets (session secret, API keys).
- Restart services after rotation: `make down && make up`
- Re-validate auth setup/session behavior.

## Export Verification
1. Unlock workspace.
2. Generate encrypted review pack from Review Pack screen.
3. Confirm export appears in history with `sha256` and `file_size`.
4. Download and confirm non-empty encrypted file.

## Troubleshooting
- Frontend not loading:
  - Check `docker compose logs frontend`
  - Verify `NEXT_PUBLIC_API_URL` points to backend host/port.
- Backend API errors:
  - Check `docker compose logs backend`
  - Validate DB file exists and is writable.
- Auth/session issues:
  - Confirm cookies are sent and CORS origin is allowed.
- Export file missing:
  - Check `data/exports/` and export metadata in API history.
  - Run cleanup if stale deleted rows remain: `make cleanup-exports`
