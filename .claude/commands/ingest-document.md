# /ingest-document

Use this command when adding, testing, or reviewing document upload and extraction behaviour.

## Task

Run the document through the ingestion workflow using `tax-document-ingestion` and project rules in `CLAUDE.md`.

## Required behaviour

1. Confirm the original file is stored immutably.
2. Capture metadata, MIME type, file size, hash, and upload timestamp.
3. Extract PDF text layer before OCR.
4. Use OCR only when text extraction is insufficient.
5. Preserve page-level text and extraction confidence where available.
6. Detect duplicates without deleting them.
7. Produce canonical ingestion JSON.
8. Validate against `skills/tax-document-ingestion/schemas/document_ingestion.schema.json`.
9. Record audit events for success or failure.

## Output expected

Return:

- document ID
- storage status
- extraction method
- extraction confidence
- duplicate status
- missing or uncertain fields
- schema validation result
- tests run

## Guardrails

- Do not discard unreadable documents.
- Do not log raw sensitive document text.
- Do not call tax classification before ingestion is complete.
