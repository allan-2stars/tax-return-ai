# Phase 7: Export Hardening

## Hardened behavior
- Stronger export password validation on server:
  - minimum 12 characters
  - rejects empty/whitespace-only
  - rejects common weak passwords list
- Download lifecycle hardening:
  - `downloaded_at` updates on successful download
  - audit event: `review_pack_downloaded`
- Export deletion endpoint added:
  - marks metadata `status=deleted`
  - clears stored path
  - deletes encrypted file if present
  - audit event: `review_pack_deleted`

## Legacy routes decision
Legacy `/api/export/*` routes are disabled by default using config flag:
- `enable_legacy_export_routes=false` (default)
- when disabled, return `410 Gone` with migration message to workspace routes

This removes risk of authenticated plaintext legacy export endpoints being used unintentionally.

## Password rules
- Required
- Minimum length 12
- Must not be whitespace-only
- Must not match common weak passwords
- Password is never logged or stored

## Metadata fields
Workspace export metadata now includes:
- `sha256`
- `file_size`
- `encryption_version`
- `kdf`
- `kdf_params_summary`
- `created_at`
- `downloaded_at`
- plus existing workspace/export record metadata

## Delete/retention behavior
Endpoint:
- `DELETE /api/workspaces/{workspace_id}/review-pack/{export_id}`

Behavior:
- auth + ownership required
- removes encrypted file if exists
- marks record deleted and unlinks storage path
- does not touch unrelated files

## UX changes
Review Pack page now includes:
- strong password guidance
- mismatch error
- minimum length hint
- non-recoverable warning text
- export history with size, sha256 preview, kdf, downloaded_at
- delete button per export row

## Test results
Commands run:
- `docker compose config`
- `make test-auth`
- `pytest -q tests/test_workspace_scoped_routes.py`
- `pytest -q tests/test_review_workflow.py`
- `pytest -q tests/test_encrypted_review_pack.py`
- `cd frontend && npm run lint`
- `cd frontend && npm run test:workspace`
- `cd frontend && npm run build`
- `make up`

## Known limitations
- Full DB encryption-at-rest still not implemented.
- Legacy export routes can still be manually enabled via env flag.
- No password recovery for encrypted review packs.

## Recommended Phase 8
- Production hardening and operational controls:
  - stricter audit monitoring and alerting
  - retention policy automation for encrypted exports
  - explicit deprecation/removal plan for legacy export code paths
  - end-to-end migration checks and backup/restore drills
