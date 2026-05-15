# Phase 10: Field-Level Encryption At Rest

## Scope
Implemented application-layer field encryption for sensitive text fields using the existing local unlock model.

## Encryption Design
- Algorithm: AES-256-GCM
- Envelope format: `enc::<json>` containing:
  - `version`
  - `alg`
  - `nonce`
  - `ciphertext`
  - `key_version`
- Nonce: random per value
- Tamper detection: provided by AEAD authentication

## Key Derivation and Runtime Handling
- Field key is derived from master password unlock material via auth KDF output.
- Raw field key is never persisted.
- Key is cached in-memory per active auth session token until session expiry/logout.
- Logout clears token-bound cached key.

## Encrypted Fields (Phase 10)
- `document_pages.text_enc` (for OCR page text)
- `tax_items.description_enc`
- `tax_items.notes_enc`
- `tax_items.review_reason_enc`
- `classification_results.raw_input_enc`
- `classification_results.raw_output_enc`

## Not Encrypted Yet
- IDs, workspace/session foreign keys, enums/status, timestamps
- Amount fields
- Filenames and storage paths
- Existing plaintext columns are retained for compatibility in this phase
- This is not whole-database encryption

## Write Path Behavior
- OCR pipeline writes to `document_pages.text_enc` when field key is available.
- Classification pipeline writes encrypted description/review reason and raw AI I/O when field key is available.
- Fallback plaintext write is retained where key is unavailable (temporary compatibility behavior).

## Read Path Behavior
- Workspace item/page reads decrypt encrypted fields for authenticated workspace owners.
- If encrypted content exists but key is unavailable: API returns `423 Locked` with unlock guidance.

## Migration and Backfill
- Additive migration adds `*_enc` and metadata columns.
- Backfill command:
  - `make encrypt-backfill-dry-run`
  - `make encrypt-backfill`
- Safety:
  - requires `--confirm`
  - idempotent
  - dry-run supported
  - logs counts only

## Rollback Plan
1. Revert Phase 10 routing/service/model changes.
2. Keep plaintext columns as authoritative source.
3. Stop using `*_enc` reads/writes.
4. Re-run focused tests.

## Limitations
- In-memory key cache is process-local and cleared on restart.
- Background processing may still write plaintext when no active key is present.
- Plaintext columns are still present and not purged in this phase.

## Recommended Phase 11
- Enforce encrypted-only writes for targeted fields.
- Add explicit key-presence checks for background jobs before sensitive writes.
- Add controlled plaintext retirement plan and migration guardrails.
