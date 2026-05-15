# Phase 15: Multi-Process Unlock / Session Capability Hardening

## Capability Model

Implemented a DB-backed unlock capability layer so unlock state is not inferred only from in-process memory.

- New table: `unlock_capabilities`
  - `user_id`
  - `auth_session_id`
  - `session_token_hash`
  - `key_epoch`
  - `created_at`, `last_seen_at`, `expires_at`, `revoked_at`
- Capabilities are short-lived and sliding:
  - issued on setup/unlock/recovery-reset
  - bounded TTL (default min of idle-timeout and 15 minutes)
  - refreshed on valid sensitive access
- Revocable by:
  - session revoke/logout
  - session expiry/auto-lock
  - user-wide revoke on password recovery reset
- Raw DEK is **never persisted** in DB.
  - DB stores only capability metadata and hashed session token reference.
  - DEK remains in memory cache tied to active session lifecycle.

## Shared Revocation / Epoch Source

Added DB-backed epoch controls:

- `users.unlock_epoch` (default `1`)
- `auth_sessions.key_epoch` snapshot

Behavior:

- On recovery reset, `users.unlock_epoch` increments.
- Existing sessions are revoked.
- Existing capabilities are revoked.
- Any stale session/capability epoch mismatch is blocked.

## Sensitive Operation Enforcement

Sensitive workspace routes now rely on all checks:

1. Auth session resolves and is not revoked/expired.
2. DB unlock capability exists, not revoked, not expired.
3. Session and user `key_epoch` match capability epoch.
4. In-process DEK key is available (for current phase decryption/write paths).

If checks fail:

- `401` for invalid/revoked auth session.
- `423` for locked/missing unlock capability or missing key state.

## Observability

Added:

- Capability metrics counters for failures:
  - `locked_or_missing`
  - `stale_epoch`
  - `revoked`
  - `expired`
- Audit events already include lock/unlock/revoke/expired paths.
- New safe endpoint: `GET /api/auth/capability-health`
  - returns counts/metrics only
  - no secrets/tokens/keys returned

## Worker-Safe Design (Future Container)

Current hardened posture:

- Worker jobs include hashed capability reference and expiry metadata.
- Worker validates capability against DB (revoked/expired checks) before proceeding.
- Worker still does not persist DEK, and no raw DEK is placed in DB.

Future multi-container handoff path:

1. API unlock issues short-lived capability metadata in DB.
2. Job enqueue records capability hash + expiry only.
3. Worker claims job and validates capability status via DB.
4. If capability invalid/expired/revoked, worker retries/fails safely without processing sensitive content.
5. Revocation is immediate from DB perspective across processes.

## Files Changed

- Model/migration:
  - [app/models/unlock_capability.py](/home/pi/tax-return-ai/app/models/unlock_capability.py)
  - [app/models/user.py](/home/pi/tax-return-ai/app/models/user.py)
  - [app/models/auth_session.py](/home/pi/tax-return-ai/app/models/auth_session.py)
  - [app/models/__init__.py](/home/pi/tax-return-ai/app/models/__init__.py)
  - [alembic/versions/011_unlock_capability_and_epoch.py](/home/pi/tax-return-ai/alembic/versions/011_unlock_capability_and_epoch.py)
- Services/deps:
  - [app/services/security/unlock_capability.py](/home/pi/tax-return-ai/app/services/security/unlock_capability.py)
  - [app/services/auth/service.py](/home/pi/tax-return-ai/app/services/auth/service.py)
  - [app/db/auth_deps.py](/home/pi/tax-return-ai/app/db/auth_deps.py)
  - [app/services/job/worker.py](/home/pi/tax-return-ai/app/services/job/worker.py)
- API:
  - [app/routers/auth.py](/home/pi/tax-return-ai/app/routers/auth.py)
- Tests:
  - [tests/test_phase15_unlock_capability.py](/home/pi/tax-return-ai/tests/test_phase15_unlock_capability.py)
  - [tests/test_worker_job_flow.py](/home/pi/tax-return-ai/tests/test_worker_job_flow.py)

## Test Results

- `make test-auth`: passed
- Phase 13/Phase 15/focused backend suites: passed
- frontend lint/test/build: passed
- `docker compose config`: passed
- `make up`: passed

## Remaining Risks

- DEK remains process-memory scoped. Full multi-process decryption execution still needs explicit distributed key-release design.
- Capability metadata is shared/revocable, but no cross-process secure DEK transport exists yet.
- Full database encryption-at-rest is still partial.

## Recommended Next Phase

- Phase 16: distributed transient key-release channel for workers (signed one-time key grants, strict TTL, immediate revoke fanout, and operational dashboards/alerts).
