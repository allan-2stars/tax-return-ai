# Legacy Route Deprecation Plan

## Purpose
Phase out session-first and legacy export APIs in favor of authenticated workspace-first routes.

## Legacy Route Inventory
| Legacy route | Current behavior | Risk | Replacement |
|---|---|---|---|
| `GET /api/export/{session_id}` | Generates legacy JSON/CSV export | High (legacy pathway) | `POST /api/workspaces/{workspace_id}/review-pack/generate` |
| `GET /api/export/{session_id}/history` | Lists session export history | Medium | `GET /api/workspaces/{workspace_id}/review-pack` |
| `POST /api/export/workspaces/{workspace_id}/review-pack` | Legacy bridge to old export | High | `POST /api/workspaces/{workspace_id}/review-pack/generate` |
| Session-first item/document routes without workspace prefix | Older access pattern | Medium | `/api/workspaces/{workspace_id}/...` |

## Current Control State
- Legacy export routes are gated by `ENABLE_LEGACY_EXPORT_ROUTES`.
- When disabled, endpoints return `410 Gone`.

## Planned Removal
1. Phase 8: Keep env-flag lockdown, publish migration guidance.
2. Phase 9: Frontend fully removes legacy calls.
3. Phase 10: Remove legacy export router handlers and tests.
4. Phase 10+: Remove compatibility bridge helpers once no live dependency remains.

## Migration Risks
- External scripts still calling `/api/export/*`.
- Historical workflows that assume session IDs only.

## Mitigations
- Keep explicit `410` response message with replacement route guidance.
- Maintain workspace-first API docs and integration tests.
