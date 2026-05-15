# Phase 9: Legacy Cutover

## Goal
Complete workspace-first cutover by disabling legacy session-first API paths that bypass the secure workflow.

## Legacy Route Inventory
| Legacy route | Workspace-first replacement | Current consumer | Action | Reason |
|---|---|---|---|---|
| `/api/export/*` | `/api/workspaces/{workspace_id}/review-pack/*` | Old scripts/tests only | Return `410 Gone` | Prevent legacy plaintext/session-first export flow |
| `/api/documents/*` | `/api/workspaces/{workspace_id}/documents` and `/upload` | Old session page/tests | Return `410 Gone` | Enforce workspace ownership boundary |
| `/api/items/*` | `/api/workspaces/{workspace_id}/items` and review-status patch | Old session page/tests | Return `410 Gone` | Remove non-workspace review mutation path |
| `/api/compliance/{session_id}` | `/api/workspaces/{workspace_id}/issues` | Old session page/tests | Return `410 Gone` | Enforce workspace-scoped issue access |
| `/api/sessions/*` | `/api/workspaces` + workspace APIs | Old session page/tests | Return `410 Gone` | Disable direct session CRUD bypass |
| `POST /api/workspaces/{workspace_id}/review-pack` (legacy JSON/CSV bridge) | `POST /api/workspaces/{workspace_id}/review-pack/generate` | Legacy clients | Return `410 Gone` | Remove non-encrypted legacy export bridge |

## What Was Disabled
- Legacy routers are no longer included in main app routing.
- New catch-all legacy-lockdown router now returns `410 Gone` for:
  - `/api/export/*`
  - `/api/sessions/*`
  - `/api/documents/*`
  - `/api/items/*`
  - `/api/compliance/*`
- Workspace-first endpoints remain active under `/api/workspaces/*`.

## Frontend Cutover Status
- `WorkspaceApp` visible navigation remains workspace-first only.
- Added frontend test assertion that no visible `/session/:id` link is rendered.
- Legacy API methods still exist in `frontend/lib/api.ts` only for non-workspace legacy page compatibility; they now receive `410` in backend.

## What Remains
- Legacy session page route (`/session/[id]`) still exists in codebase but is effectively non-functional against disabled API paths.
- Full removal of obsolete page/components can be done in next phase after confirming no dependency.

## Rollback Plan
1. Re-enable legacy routers in `app/main.py`.
2. Remove legacy-lockdown router include.
3. Re-run full API test matrix.
4. Re-check auth/workspace ownership coverage before exposing legacy routes again.

## Test Results
See `docs/LEGACY_ROUTE_DEPRECATION_PLAN.md` and this phase execution output for command-level results.
