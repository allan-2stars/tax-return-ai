# /classify-document

Use this command when classifying a newly uploaded document or validating the classification workflow for a document.

## Task

Classify the target document using the `tax-return-specialist` skill and the project architecture rules in `CLAUDE.md`.

## Required behaviour

1. Confirm the document has a persisted `documents` record.
2. Confirm extracted text exists or run the extraction pipeline.
3. Preserve raw extracted text and document/page references.
4. Classify candidate tax items using the schema-versioned output contract.
5. Store classification results separately from extracted items.
6. Mark uncertainty explicitly with confidence, risk, evidence status, and review status.
7. Never mark an item as final or guaranteed.
8. Add audit events for classification and any user-confirmed changes.

## Output expected

Return a concise implementation or review summary including:

- document status before and after
- number of extracted items
- number of classification results
- items needing user review
- items needing tax agent review
- schema validation status
- tests run

## Guardrails

- Do not call an AI provider SDK directly from business logic.
- Use the AI adapter interface.
- Do not hard-code one database or storage backend.
- Do not discard source evidence.
- Do not invent tax rules or thresholds.
