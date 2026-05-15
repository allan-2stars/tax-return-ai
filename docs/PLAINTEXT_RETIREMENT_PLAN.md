# Plaintext Retirement Plan

## Objective
Retire plaintext fallback reads/writes safely after migration completion, without data loss and with rollback options.

## Current State
- Field-level encryption is active for sensitive fields.
- Plaintext columns still exist for backward compatibility.
- Some routes still support plaintext fallback reads for legacy rows.

## Migration Phases

1. Visibility Phase
- Use workspace security status endpoint to monitor:
  - plaintext-only rows
  - encrypted rows
  - mixed rows
  - migration completion percentage
- Track per table:
  - `document_pages`
  - `tax_items`
  - `classification_results`

2. Backfill Phase
- Run idempotent backfill in controlled batches.
- Re-run readiness report until plaintext-only rows reach zero.
- Keep fallback reads enabled during this phase.

3. Soft-Disable Phase
- Add config flag to disable plaintext fallback reads in staging/test.
- Validate core flows:
  - workspace item review
  - document page viewing
  - export generation
- Monitor locked-write/failed-decrypt and support incidents.

4. Production Disable Phase
- Enable fallback disable only when:
  - plaintext-only rows are zero for all target tables
  - mixed rows are understood/acceptable
  - no critical decrypt errors for a defined observation window

5. Column Retirement Phase
- After stable fallback-disable window, remove plaintext columns in additive-safe migrations.

## Fallback Disable Strategy
- Add a runtime feature flag (future phase) for plaintext fallback reads.
- Roll out by environment:
  - local dev -> staging -> production
- Keep emergency rollback path to re-enable fallback quickly.

## Rollback Strategy
- If regressions occur:
  - re-enable plaintext fallback flag
  - keep encrypted writes active
  - restore from backups if needed
  - analyze blocked entities from audit/security status endpoints

## Safe Column Removal Sequence
Recommended order (after zero plaintext-only + stable operations):
1. `classification_results.raw_input`, `classification_results.raw_output`
2. `tax_items.description`, `tax_items.notes`, `tax_items.review_reason`
3. `document_pages.text`

For each removal:
- add migration
- deploy
- verify API and UI behavior
- monitor audit/error counters

## Read Paths To Eliminate Before Removal
- `workspaces.list_workspace_items` plaintext fallback
- `workspaces.list_workspace_document_pages` plaintext fallback
- classification legacy plaintext fallback readers

## Gate Criteria Before Final Removal
- `can_disable_plaintext_fallback = true` for all active workspaces sampled.
- No critical decrypt failures in production monitoring window.
- Backup/restore rehearsal completed.
- Rollback plan rehearsed.
