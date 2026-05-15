# Phase 14: Production Cookie and Session Security Hardening

## Implemented Security Changes

- Added environment-driven cookie security config in [app/config.py](/home/pi/tax-return-ai/app/config.py):
  - `cookie_secure` (default `true`)
  - `cookie_samesite` (default `lax`)
  - `cookie_domain` (optional)
  - `allow_insecure_cookie_local_dev` (default `false`)
- Added explicit session timeout config aliases:
  - `session_idle_timeout_minutes` / `session_idle_timeout_seconds`
  - `session_absolute_timeout_hours` / `session_absolute_timeout_seconds`
  - effective properties normalize values for runtime checks and cookie max-age.
- Hardened auth cookie handling in [app/routers/auth.py](/home/pi/tax-return-ai/app/routers/auth.py):
  - centralized `_set_auth_cookie(...)` and `_clear_auth_cookie(...)`
  - cookies now consistently set `HttpOnly`, configured `Secure`, `SameSite`, optional `Domain`, and timeout-based `max_age`
  - logout uses aligned cookie-clear attributes to avoid stale cookie retention.
- Session service updates in [app/services/auth/service.py](/home/pi/tax-return-ai/app/services/auth/service.py):
  - session expiry now uses effective timeout config values
  - added `invalid_session_token` audit event (token hash only, no raw token) for suspicious cookie/token use.
- Updated `.env` template in [.env.example](/home/pi/tax-return-ai/.env.example) with cookie/session security flags.

## Cloudflare / TLS Recommendations

For HTTPS deployment behind Cloudflare:

- Set `COOKIE_SECURE=true`.
- Set `COOKIE_SAMESITE=lax` (or `strict` if cross-origin post-auth flows are not needed).
- Set `COOKIE_DOMAIN` only if cookie must be shared across subdomains; otherwise keep blank.
- Keep `ALLOW_INSECURE_COOKIE_LOCAL_DEV=false` in production.
- Ensure Cloudflare always terminates TLS and origin path remains private (`127.0.0.1` bindings are already used).
- Use strict HTTPS redirect policy at Cloudflare edge and origin.

## Local Development Behavior

- Insecure cookies are only possible when explicitly configured:
  - `COOKIE_SECURE=false`
  - `ALLOW_INSECURE_COOKIE_LOCAL_DEV=true`
- This keeps local testing workable while preventing accidental insecure defaults.

## Verification

Commands run:

```bash
docker compose config
make test-auth
./.venv/bin/pytest -q tests/test_phase13_unlock_lifecycle.py
cd frontend && npm run lint
cd frontend && npm run test:workspace
cd frontend && npm run build
make up
```

Additional checks included:

- production cookie attributes test
- explicit local dev insecure-cookie test
- logout cookie clear test
- expired/locked session behavior test
- frontend 401/423 locked-state handling tests

## Remaining Risks

- DEK/session unlock cache is still process-local (shared broker deferred to next phase).
- Cookie hardening does not replace host-level compromise protections.
- Full database encryption-at-rest remains partial (field-level only at this stage).

## Next Phase Recommendation

- Phase 15: distributed/session-capability hardening for multi-process runtime (shared revocation, unlock capability coordination, and operational monitoring).
