# Phase 12: Background Worker + Encryption Lifecycle Architecture

## Architecture Changes
- Extended `jobs` model with worker/lease/capability metadata:
  - `workspace_id`, `user_id`
  - `requires_encryption`
  - `capability_token_hash`, `capability_expires_at`
  - `payload`
  - `lease_owner`, `lease_expires_at`, `heartbeat_at`, `attempt_count`
- Added worker execution primitives:
  - `claim_next_job`
  - `heartbeat_job`
  - `execute_job`
- Added token-hash key lookup helper for capability validation in worker flow.
- Workspace upload/export job creation now records encryption capability metadata.

## Key Lifecycle Model
- API process still derives key at unlock and stores key in volatile in-memory cache.
- Jobs carry only capability hash + expiry metadata, never raw key.
- Worker execution validates capability by hash and expiry.
- If capability unavailable/expired, job is moved to `retrying` with safe error state.

## Worker-Aware Flow (Current)
- OCR/classification: existing ingestion job now carries workspace/capability metadata.
- Review-pack generation: now tracked via explicit export job lifecycle states.
- Worker service currently provides lifecycle/capability enforcement primitives and is ready for dedicated worker container wiring.

## Safety Properties
- No permanent worker-side master key storage.
- No raw master/encryption key persisted to DB.
- Workspace/user scope attached to jobs for isolation checks.
- Encrypted-only sensitive writes remain enforced.

## Pi-Friendly and Restart Considerations
- No Redis dependency added.
- DB-backed queue/lease state supports restart-safe job visibility.
- Key cache remains process-local; after restart, locked-key jobs safely enter retrying until unlock restores capability.

## Operational Notes
- Worker id should be unique per process/container for lease ownership.
- Lease heartbeat cadence should be below lease expiry (for future dedicated worker loop).
- Jobs with `encryption_key_missing` should be retried after user unlock.

## Remaining Risks
- Key cache is not shared across multiple API/worker processes yet.
- Cross-container worker execution requires shared capability/key-provider backend in future phase.
- Payload format governance/versioning remains lightweight.

## Rollback Plan
1. Revert worker-capability usage in job creation paths.
2. Keep job model additive fields (safe no-op).
3. Continue processing via existing in-process background execution.
4. Re-run focused job/encryption suites.

## Recommended Next Phase
- Phase 13: introduce shared ephemeral capability/key broker for true multi-container worker execution, with strict TTL and revocation semantics.
