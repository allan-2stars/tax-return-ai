# Phase 6: Encrypted Workspace Review Pack

## Export format
Generated filename pattern:
- `tax-review-pack-<id>.enc.zip`

Package plaintext contents before encryption:
- `review-report.json`
- `extracted-items.json`
- `evidence-index.csv`
- `metadata.json`

## Encryption approach
- Symmetric authenticated encryption: `AES-256-GCM`
- KDF:
  - `argon2id` when available
  - fallback `PBKDF2-SHA256` with 600,000 iterations
- Envelope stores only non-secret metadata:
  - version
  - algorithm
  - kdf + params
  - salt
  - nonce

Security rules implemented:
- export password is never logged
- export password is never stored
- encrypted blob is stored on filesystem and streamed for download
- server never decrypts on download

## Metadata-only DB behavior
`export_packages` now stores metadata for workspace export history:
- id
- workspace_id
- filename
- status
- format
- encrypted
- kdf
- created_at
- downloaded_at
- file_size
- sha256
- item_count
- document_count
- blocking_reasons snapshot
- storage_path

Plaintext payload persistence is disabled in the new workspace export flow.

## Routes added
- `POST /api/workspaces/{workspace_id}/review-pack/generate`
- `GET /api/workspaces/{workspace_id}/review-pack`
- `GET /api/workspaces/{workspace_id}/review-pack/{export_id}/download`

Rules:
- auth required
- workspace ownership required
- generation blocked if `review-summary.ready_for_export=false`

## UX changes
Review Pack panel now:
- shows readiness and blockers
- requests export password + confirmation
- warns user to save the password
- generates encrypted review pack
- shows export history and download links

## Security limitations
- full database encryption-at-rest is still not implemented
- public-key sharing / agent key exchange is not implemented
- include-source-documents option is not supported in MVP export path yet

## Not implemented yet
- client-side decryption helper
- key escrow/recovery for export passwords
- signed package verification workflow

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

## Rollback plan
1. Downgrade migration `006_workspace_encrypted_export_metadata.py`.
2. Revert workspace review-pack generate/history/download routes.
3. Revert encrypted export service and UI wiring for password-based export.
4. Keep Phase 5 review workflow endpoints and legacy export routes active.
