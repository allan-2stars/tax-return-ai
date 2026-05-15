# Phase 13: Session Unlock Lifecycle Hardening

## Implemented Lifecycle/Security Changes

- Added configurable session lock controls in [app/config.py](/home/pi/tax-return-ai/app/config.py):
  - `session_idle_timeout_minutes` (default `30`)
  - `session_absolute_timeout_hours` (default `12`)
  - `lock_on_browser_close` (default `false`)
- Hardened auth/session lifecycle in [app/services/auth/service.py](/home/pi/tax-return-ai/app/services/auth/service.py):
  - `resolve_session(...)` now enforces idle timeout and absolute timeout in addition to `expires_at`.
  - Expired/idle sessions revoke unlock state and clear DEK cache entries.
  - Logout clears DEK cache by token and token hash.
  - Recovery password reset revokes prior active sessions and clears user DEK cache entries.
- Added DEK cache lifecycle helpers in [app/services/security/key_cache.py](/home/pi/tax-return-ai/app/services/security/key_cache.py):
  - `clear_session_key_by_hash(...)`
  - `clear_user_keys(...)`
- Added unlocked-state dependency in [app/db/auth_deps.py](/home/pi/tax-return-ai/app/db/auth_deps.py):
  - `get_current_unlocked_user(...)` enforces authenticated + active DEK state.
  - Returns `423 Locked` with consistent message when key is unavailable.
- Applied unlock enforcement to sensitive workspace-first routes in [app/routers/workspaces.py](/home/pi/tax-return-ai/app/routers/workspaces.py):
  - document reads
  - item reads/updates
  - review summary/issues
  - review-pack generate/list/download/delete/cleanup
  - audit-event listing
- Added audit events (without sensitive payload values):
  - `workspace_unlocked`
  - `workspace_locked`
  - `auto_lock_triggered`
  - `session_expired`
  - `recovery_reset_completed`

## Timeout/Lock Model

- Session is treated as invalid and locked if any condition is true:
  - revoked
  - absolute TTL reached
  - idle timeout reached
  - explicit `expires_at` reached
- On lock/expiry:
  - session DEK cache entry is removed
  - API returns non-authenticated session state (`SESSION_EXPIRED` from `/api/auth/session`)
  - sensitive routes reject with `423` if authenticated but DEK-unlocked state is missing

## Frontend Multi-Tab + Unlock UX

Changes in [frontend/components/workspace/WorkspaceApp.tsx](/home/pi/tax-return-ai/frontend/components/workspace/WorkspaceApp.tsx):

- Added periodic session validation when unlocked (60s cadence) to detect expiry/lock.
- Added cross-tab synchronization via `localStorage` (`taxai_auth_event`):
  - `locked`, `expired`, `unlocked` propagation.
- Added explicit **Lock Workspace** button.
- Added locked-response handling for 401/423-sensitive actions.
- Added optional browser-close lock best-effort behavior (gated by `NEXT_PUBLIC_LOCK_ON_BROWSER_CLOSE`) via `authLogoutKeepalive` in [frontend/lib/api.ts](/home/pi/tax-return-ai/frontend/lib/api.ts).

## Tests and Verification

Commands run:

```bash
docker compose config
make test-auth
./.venv/bin/pytest -q tests/test_phase13_unlock_lifecycle.py
./.venv/bin/pytest -q tests/test_workspace_scoped_routes.py tests/test_review_workflow.py tests/test_encrypted_review_pack.py tests/test_field_encryption.py
cd frontend && npm run lint
cd frontend && npm run test:workspace
cd frontend && npm run build
make up
```

Results:

- `docker compose config`: passed
- `make test-auth`: passed (`10 passed`)
- `tests/test_phase13_unlock_lifecycle.py`: passed (`4 passed`)
- focused backend suites: passed (`29 passed`)
- frontend lint: passed
- frontend workspace tests: passed (`16 passed`)
- frontend build: passed
- `make up`: passed; services started healthy

## Operational Risks / Scaling Notes

- DEK cache remains in-process memory; multi-process/multi-node runtime needs a shared secure unlock-capability strategy in next phase.
- Browser-close lock remains best-effort and environment/browser dependent.
- Idle timeout relies on API activity heartbeat (`last_seen_at` updates); fully passive UI tabs may transition to lock between polls.
- Auth cookie remains `secure=False` in current local setup and should be tightened for production TLS-only cookie policy.

## Future Scaling Considerations

- Move unlock capability lifecycle to a process-safe secure coordinator for worker/runtime scaling.
- Add bounded cache eviction policy metrics and observability for key-cache pressure.
- Add server push (or lightweight websocket/event channel) for lower-latency cross-tab/session invalidation.
