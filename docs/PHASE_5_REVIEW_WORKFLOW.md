# Phase 5: Workspace-First Review Workflow

## Summary
Phase 5 introduces explicit review status lifecycle for items and workspace-first review workflow APIs, while keeping legacy item routes available for compatibility.

## Model changes
- `tax_items.review_status` added with values:
  - `draft`
  - `needs_review`
  - `confirmed`
  - `excluded`
  - `tax_agent_review`
- Backward compatibility preserved:
  - `needs_review` boolean remains in model/routes.

## Status mapping
Migration maps existing rows:
- `needs_review = true` -> `review_status = needs_review`
- `needs_review = false` -> `review_status = confirmed`

Runtime sync rules:
- setting `review_status=confirmed|excluded` sets `needs_review=false`
- setting `review_status=needs_review|tax_agent_review|draft` sets `needs_review=true`

## Migration
- Added: `alembic/versions/005_add_review_status_to_tax_items.py`
  - adds `review_status` column (default `needs_review`)
  - backfills data from `needs_review`
  - adds `ix_tax_items_review_status`

## Routes added/updated
Preferred workspace-first routes:
- `GET /api/workspaces/{workspace_id}/items?review_status=...`
- `PATCH /api/workspaces/{workspace_id}/items/{item_id}/review-status`
- `GET /api/workspaces/{workspace_id}/review-summary`

Patch payload:
```json
{
  "review_status": "confirmed | needs_review | excluded | tax_agent_review",
  "note": "optional reviewer note"
}
```

Auth and ownership:
- auth required
- workspace ownership required
- item must belong to selected workspace
- wrong workspace/user => `404`

Audit:
- each status transition writes `review_status_updated`
- event details include only from/to status + note presence (no raw sensitive values)

## Review summary rules
`ready_for_export=false` when:
- no items
- any `draft`
- any `needs_review`
- any `tax_agent_review`

`excluded` items do not block export.

## Frontend workflow changes
Workspace shell updated to use workspace-first review APIs:
- Dashboard uses `review-summary` for progress
- Review Pack step is disabled when `ready_for_export=false`
- Review Items shows status filters:
  - All / Needs Review / Confirmed / Excluded / Tax Agent Review
- Item actions:
  - Confirm
  - Needs Review
  - Exclude
  - Tax Agent Review
- Issues page placeholder is explicit:
  - "No dedicated issue engine yet"
  - "Items marked Tax Agent Review will appear here"

## Test results
Commands run:
- `docker compose config` -> pass
- `make test-auth` -> pass
- `./.venv/bin/pytest -q tests/test_workspace_scoped_routes.py` -> pass
- `./.venv/bin/pytest -q tests/test_review_workflow.py` -> pass
- `cd frontend && npm run lint` -> pass
- `cd frontend && npm run test:workspace` -> pass

## Known limitations
- Compliance/issue engine is still not complete.
- Encryption-at-rest is not implemented yet.
- Legacy item/session routes remain for compatibility and should be retired in a later phase.

## Rollback plan
1. Downgrade migration `005_add_review_status_to_tax_items.py`.
2. Revert workspace review-status and summary routes.
3. Revert WorkspaceApp review status UI wiring.
4. Keep Phase 4 workspace-scoping baseline active.
