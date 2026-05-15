# Phase 4: Workspace-Scoped Documents and Review Routes

## Summary
Phase 4 adds authenticated workspace scoping for document, item, issues/compliance, and review-pack/export access.
The implementation is additive and keeps legacy session-centric routes for compatibility while introducing preferred workspace URLs.

## Data model changes
- Added `tax_sessions.workspace_id` (nullable FK to `tax_workspaces.id`).
- This is a compatibility bridge so existing legacy sessions remain readable and can be mapped safely.

## Migration notes
- New migration: `alembic/versions/004_add_workspace_id_to_tax_sessions.py`
  - adds nullable `workspace_id`
  - adds index `ix_tax_sessions_workspace_id`
  - adds FK `tax_sessions.workspace_id -> tax_workspaces.id`
- Legacy rows are not dropped or rewritten.
- Legacy bridge in code:
  - when a legacy `tax_session` has `workspace_id = NULL`, ownership checks map it to a user workspace (prefer matching financial year, else first user workspace) and persist the mapping.

## Routes protected
All below now require authenticated session and ownership checks.

### Preferred workspace routes
- `GET /api/workspaces/{workspace_id}/documents`
- `POST /api/workspaces/{workspace_id}/documents/upload`
- `GET /api/workspaces/{workspace_id}/items`
- `GET /api/workspaces/{workspace_id}/issues`
- `POST /api/workspaces/{workspace_id}/review-pack`

### Protected legacy routes (compatibility)
- Document routes under `/api/documents/*`
- Item routes under `/api/items/*`
- Export routes under `/api/export/*`
- Compliance route `/api/compliance/{session_id}`

Unauthenticated requests return `401`.
Wrong-ownership workspace/session/doc/item requests return `404` (consistent anti-enumeration behavior).

## Routes still legacy
- Session-centric endpoints (`/api/sessions/*`) remain legacy and are not fully workspace-first yet.
- Legacy document/item/export/compliance routes are still available temporarily and marked in code comments where applicable.

## Audit events added/updated
- `document_uploaded` intent retained via existing upload audit entry (`action=uploaded`, no raw text logged).
- `document_deleted` recorded with explicit event detail.
- Item review audit now emits:
  - `item_confirmed`
  - `item_excluded`
  - `item_tax_agent_review`
  - fallback `flagged_for_review`
- Review-pack generation audit includes event detail `review_pack_generated`.

No raw document text or sensitive extracted payload values are written to audit details.

## Security limitations
- Workspace lock/auth is implemented, but encryption-at-rest is not complete yet.
- Legacy routes remain temporarily for compatibility and still depend on session-to-workspace bridge.
- Single active local user model remains in this phase.

## Test results
Commands run:
- `docker compose config` -> pass
- `make test-auth` -> pass
- `./.venv/bin/pytest -q tests/test_workspace_scoped_routes.py` -> pass
- `cd frontend && npm run lint` -> pass
- `cd frontend && npm run test:workspace` -> pass

## Rollback plan
1. Revert migration `004_add_workspace_id_to_tax_sessions.py` (downgrade).
2. Revert router-level auth/ownership guards for workspace-scoped additions.
3. Revert workspace bridge helper (`app/db/workspace_scope.py`).
4. Keep existing Phase 3 auth/workspace baseline intact.
