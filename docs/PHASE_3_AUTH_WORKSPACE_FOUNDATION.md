# Phase 3 — Auth & Workspace Foundation

## Implemented models
Added additive database models (and migration) for:
- `users`
- `auth_sessions`
- `tax_workspaces`

Model fields implemented:
- User: `id`, `email`, `display_name`, `password_kdf`, `password_salt`, `password_hash`, `recovery_key_salt`, `recovery_key_hash`, `created_at`, `updated_at`, `last_unlocked_at`, `is_active`
- AuthSession: `id`, `user_id`, `session_token_hash`, `created_at`, `expires_at`, `revoked_at`, `last_seen_at`, `user_agent`, `ip_hash`
- TaxWorkspace: `id`, `user_id`, `tax_year`, `label`, `status`, `created_at`, `updated_at`, `last_opened_at`

Migration file:
- `alembic/versions/003_add_auth_and_workspaces.py`

## Implemented routes
### Auth routes
- `GET /api/auth/setup-status`
- `POST /api/auth/setup`
- `POST /api/auth/unlock`
- `POST /api/auth/logout`
- `GET /api/auth/session`

### Workspace routes
- `GET /api/workspaces` (auth required)
- `POST /api/workspaces` (auth required)

## Session/auth behavior
- Master password is never stored in plaintext.
- Password hash derivation:
  - Argon2id when available
  - PBKDF2-SHA256 fallback with strong iterations when Argon2 is unavailable
- Recovery key generated once on setup; only recovery key hash is persisted.
- Session token is random; only token hash is persisted.
- Session cookie support added (`taxai_session`) with `HttpOnly` and `SameSite=Lax`.
- Session expiry/revocation supported.

## Frontend integration
- Phase 2 mock auth/workspace usage was removed from production path in `WorkspaceApp`.
- `WorkspaceApp` now calls backend APIs:
  - setup status
  - session status
  - setup
  - unlock
  - logout
  - workspace listing
- Tax year selector now loads from backend workspaces.

## Security limitations (explicit)
- Workspace lock/session foundation is implemented.
- Full encrypted document storage at rest is **not** implemented in this phase.
- Full route protection across all legacy routes is **not** implemented in this phase.
- Cookie hardening for strict production transport settings (e.g., secure cookies behind TLS-only trust config) will be tightened in later phases.

## What remains mock
- No mock auth/workspace is used in the main frontend runtime path.
- Legacy mock files may remain only for transitional testing/reference cleanup.

## Existing route protection plan (next phase)
- Current phase protects new `workspaces` routes.
- Existing legacy document/session/item/export routes remain available for compatibility.
- Next phase will progressively enforce `require authenticated session` across legacy routes with staged rollout and compatibility checks.

## Test results
- Added backend tests for:
  - setup status
  - first setup
  - preventing second setup
  - unlock success/failure
  - logout
  - workspace auth requirement
  - workspace create/list
- Added frontend state tests for API-backed auth/workspace shell.

(See command output in implementation run for final pass/fail details.)

## Rollback plan
1. Revert commit containing auth/workspace model/router/service changes.
2. Roll back migration `003_add_auth_and_workspaces` if applied.
3. Restore previous frontend shell behavior by reverting `WorkspaceApp` and API client additions.
4. Rebuild/restart containers.
