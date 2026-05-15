# Phase 11: Encrypted-Only Writes

## Enforced Behavior
- New sensitive writes now require an active field encryption key.
- Sensitive fields are written as encrypted payloads only (`*_enc`).
- Plaintext fallback writes are blocked.

## Sensitive Fields in Scope
- `document_pages.text` -> `document_pages.text_enc`
- `tax_items.description` -> `tax_items.description_enc`
- `tax_items.notes` -> `tax_items.notes_enc`
- `tax_items.review_reason` -> `tax_items.review_reason_enc`
- `classification_results.raw_input` -> `classification_results.raw_input_enc`
- `classification_results.raw_output` -> `classification_results.raw_output_enc`

## Key-Availability Enforcement
- OCR write path blocks when key is unavailable.
- Classification write path blocks when key is unavailable.
- Review-status note update path blocks when key is unavailable.
- Blocking behavior returns/raises locked-key errors and avoids partial plaintext sensitive writes.

## Read Strategy During Migration
- Read encrypted first and decrypt when key is present.
- If no encrypted value exists, plaintext legacy value is still returned for compatibility.
- Legacy plaintext reads emit `plaintext_legacy_read` audit events.

## Audit Events Added
- `encryption_key_missing`
- `encrypted_write_blocked`
- `plaintext_legacy_read`

Notes:
- Audit details exclude decrypted/plaintext sensitive values.

## Risks
- Existing legacy plaintext rows remain until migration completion.
- Background job paths still depend on runtime in-memory key cache availability.
- Key cache is process-local and clears on restart.

## Rollback Plan
1. Re-enable plaintext fallback writes in OCR/classification/review paths.
2. Keep encrypted fields intact.
3. Re-run field-encryption and workspace test suites.
4. Re-validate no data-loss regressions.

## Next Phase Recommendation
- Phase 12: controlled legacy plaintext retirement and migration completeness checks.
  - Add migration-completion metrics.
  - Add admin-safe report for remaining plaintext rows.
  - Begin staged removal plan for plaintext read fallback.
