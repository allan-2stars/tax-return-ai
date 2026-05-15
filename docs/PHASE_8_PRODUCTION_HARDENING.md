# Phase 8: Production Hardening

## Implemented Changes
- Added encrypted review-pack cleanup service: `app/services/export/cleanup.py`.
- Added cleanup command: `scripts/cleanup_exports.py` and `make cleanup-exports`.
- Added workspace-scoped audit endpoint:
  - `GET /api/workspaces/{workspace_id}/audit-events`
  - auth required
  - ownership required
  - newest-first ordering
  - pagination via `limit` and `offset`
- Added optional workspace cleanup endpoint:
  - `POST /api/workspaces/{workspace_id}/review-pack/cleanup`
- Added frontend audit visibility panel in workspace shell (Recent Activity).

## Cleanup Behavior
- Always processes records with `status=deleted`:
  - if `storage_path` is already null: no-op
  - if file exists: delete file and clear `storage_path`
  - if file missing: no-op and clear `storage_path`
- Optional age-based cleanup (`older_than_days`):
  - marks old exports as deleted and clears file
  - **does not delete ready exports unless `include_ready_exports=true`**

## Audit Endpoint Behavior
- Route: `GET /api/workspaces/{workspace_id}/audit-events`
- Security:
  - requires active auth session
  - requires workspace ownership
- Scope:
  - includes workspace/session/document/item/export events related to selected workspace
- Output safety:
  - details payload is sanitized for raw text/content-like keys

## Legacy Route Decision
- Legacy export routes remain gated by `ENABLE_LEGACY_EXPORT_ROUTES`.
- Recommended production setting: disabled, returning `410 Gone`.
- Formal removal plan documented in `docs/LEGACY_ROUTE_DEPRECATION_PLAN.md`.

## Documentation Created
- `docs/OPERATIONAL_RUNBOOK.md`
- `docs/LEGACY_ROUTE_DEPRECATION_PLAN.md`
- `docs/SECURITY_CHECKLIST_MVP.md`

## Test Results
Commands run:
- `docker compose config`
- `./.venv/bin/pytest -q tests/test_auth_workspace.py`
- `./.venv/bin/pytest -q tests/test_workspace_scoped_routes.py`
- `./.venv/bin/pytest -q tests/test_review_workflow.py`
- `./.venv/bin/pytest -q tests/test_encrypted_review_pack.py`
- `./.venv/bin/pytest -q tests/test_phase8_hardening.py`
- `cd frontend && npm run lint`
- `cd frontend && npm run test:workspace`
- `cd frontend && npm run build`
- `make up`

Results:
- Backend focused suites passed.
- New Phase 8 hardening tests passed.
- Frontend lint passed.
- Frontend workspace test suite passed.
- Frontend production build passed.
- Docker compose startup passed.

## Known Limitations
- Full DB encryption-at-rest is still not implemented.
- Local storage risk remains if host filesystem is compromised.
- Secure wipe guarantees depend on underlying filesystem behavior.
- Legacy non-workspace routes still exist and require phased removal.

## Rollback Plan
1. Revert Phase 8 files and route additions.
2. Rebuild containers.
3. Re-run focused test matrix.
4. Keep legacy export gating enabled during rollback window.

## Recommended Phase 9
- Complete workspace-first route migration and remove legacy route usage from frontend.
- Add explicit operational metrics/alerts for failed exports, auth failures, and cleanup runs.
- Add automated backup integrity checks and restore drills.
