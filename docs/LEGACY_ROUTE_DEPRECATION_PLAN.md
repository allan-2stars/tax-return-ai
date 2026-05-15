# Legacy Route Deprecation Plan

## Purpose
Phase out session-first and legacy export APIs in favor of authenticated workspace-first routes.

## Current State (Phase 9)
- Legacy APIs are actively disabled with `410 Gone` via `app/routers/legacy.py`.
- Workspace-first routes under `/api/workspaces/*` are the supported API surface.

## Route Matrix
| Legacy route family | Status | Replacement |
|---|---|---|
| `/api/export/*` | Disabled (`410 Gone`) | `/api/workspaces/{workspace_id}/review-pack/*` |
| `/api/sessions/*` | Disabled (`410 Gone`) | `/api/workspaces` + scoped workflow endpoints |
| `/api/documents/*` | Disabled (`410 Gone`) | `/api/workspaces/{workspace_id}/documents*` |
| `/api/items/*` | Disabled (`410 Gone`) | `/api/workspaces/{workspace_id}/items*` |
| `/api/compliance/*` | Disabled (`410 Gone`) | `/api/workspaces/{workspace_id}/issues` |
| `POST /api/workspaces/{workspace_id}/review-pack` (legacy JSON/CSV) | Disabled (`410 Gone`) | `POST /api/workspaces/{workspace_id}/review-pack/generate` |

## Risks
- Any external script still calling legacy endpoints will fail fast with `410`.
- Legacy UI page `/session/[id]` remains in code and should be removed once not needed.

## Mitigations
- Consistent `410` error messages point to workspace-first replacements.
- Workspace-first integration tests remain in required CI/test matrix.

## Planned Next Step
- Phase 10: remove obsolete legacy router modules and stale legacy frontend page/components after dependency confirmation.
