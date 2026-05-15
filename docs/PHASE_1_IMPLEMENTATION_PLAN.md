# Phase 1 Implementation Plan — Tax Return AI

Phase intent: product definition, security-first information architecture, and guided workflow foundation.

Constraints for this phase:
- Use existing repository as scaffolding
- No rewrite-from-scratch
- Do not change OCR provider logic
- Do not change AI provider logic
- Do not break Docker Compose
- Do not expose secrets

## 1) File-by-file implementation plan

## Documentation (this phase)
- `docs/PRODUCT_VISION_V2.md`
- `docs/USER_WORKFLOW_V2.md`
- `docs/SECURITY_MODEL_V2.md`
- `docs/DATA_MODEL_V2.md`
- `docs/PHASE_1_IMPLEMENTATION_PLAN.md`

Purpose now: define product boundaries, workflow IA, security model, and target schema before code migration.

## Backend files to change in next step (Phase 1 implementation follow-up)
- `app/models/`
  - Add new models incrementally: `user`, `auth_session`, `tax_workspace`, `review_issue`, `encryption_key_metadata`
  - Introduce enum scaffolding for `DocumentStatus`, `ExtractedItemStatus`, `ExportStatus`
  - Keep existing `document`, `tax_item`, `export_package`, `audit_log` compatible during transition
- `alembic/versions/`
  - Add new migration file(s) only
  - No edits to existing migrations
- `app/schemas/`
  - Add target request/response schemas for unlock/session/workspace and status enums
- `app/routers/`
  - Add unlock/auth routes and workspace routes with feature-flag gating
  - Preserve existing session/document/item/export routes while migration is staged
- `app/services/`
  - Add auth/session services and event logging helpers
  - Keep ingestion/classification/OCR/export business logic behavior unchanged
- `app/repositories/`
  - Add repositories for new entities and start moving new DB access there
  - Avoid refactoring all existing routes in one change
- `app/config.py`
  - Add security/session settings flags and defaults
  - Keep current env compatibility
- `frontend/app/` and `frontend/components/`
  - Add unlock and workspace navigation shells
  - Add guided-page scaffolding while retaining existing pages/components

## Tests to add/update in next step
- `tests/`
  - New auth/session tests
  - Enum/status transition tests
  - Backward compatibility tests for existing routes during migration window
- `frontend/tests/`
  - Unlock/workspace shell behavior tests
  - Guided workflow navigation tests

## 2) What to change now
- Finalize and approve product/security/data/workflow definitions
- Align naming and lifecycle states for future code migrations
- Identify additive migration strategy to preserve running app behavior

## 3) What not to change yet
- OCR provider selection, dispatch, extraction logic
- AI provider selection, prompt, classification provider behavior
- Docker Compose service topology and health-check pattern
- Existing live route contracts unless explicitly versioned
- Existing environment variable names used by Compose/runtime

## 4) Migration risks
- Table/entity rename risk: `tax_sessions` vs target `TaxWorkspace` can break existing route assumptions
- Status migration risk: boolean `needs_review` to enum can break frontend filters and compliance logic
- Audit table naming drift risk: current `audit_logs` vs target `AuditEvent`
- Export persistence change risk: removing stored payload too early can break export history UI expectations
- Auth gate introduction risk: can block legacy endpoints if staged incorrectly

Mitigation:
- Prefer additive schema and dual-read/dual-write transition period
- Introduce compatibility adapters in schemas/services
- Migrate frontend in lockstep with backend API versioning where needed

## 5) Docker risks
- Migration scripts that assume unavailable services can fail container startup
- New env vars without defaults can cause runtime boot failures
- Added dependencies can increase image size and startup latency

Mitigation:
- Keep Compose unchanged this phase
- Add only backward-compatible env defaults
- Validate `docker compose up` and health endpoint after each migration step

## 6) Test plan
- Baseline: run current backend/frontend tests before code changes
- Additive checks:
  - new model migration applies and rolls forward cleanly
  - legacy APIs still pass smoke tests
  - unlock/session flow tests (success, lock timeout, invalid unlock)
  - status enum validation tests
- Integration checks:
  - upload -> process -> review -> export still works on existing scaffold
  - no changes to OCR/AI behavior observed
- Docker checks:
  - `docker compose up -d --build`
  - backend `/api/health` healthy
  - frontend reaches API URL as configured

## 7) Rollback plan
- Create migration per small unit; do not bundle unrelated schema changes
- Tag/commit before each migration batch
- If failure occurs:
  - stop deployment
  - revert to previous commit/tag
  - restore previous database snapshot
  - rerun stable Compose stack
- Keep old API paths active until frontend cutover completes

## 8) Recommended execution order after this planning phase
1. Add auth/user/session models and migrations (additive only)
2. Introduce unlock endpoints and session middleware behind feature flag
3. Add workspace abstraction and mapping to existing session behavior
4. Add enum-based status fields in parallel with existing fields
5. Add guided frontend shell while preserving current tabbed routes as fallback
6. Cut over route-by-route with tests and rollback checkpoints
