# /validate-schema

Use this command when validating tax analysis JSON output, ingestion output, compliance review output, API responses, fixtures, or example files.

## Task

Validate all relevant generated JSON against the current schema files.

## Schemas to check

- `skills/tax-return-specialist/schemas/tax_analysis_output.schema.json`
- `skills/tax-document-ingestion/schemas/document_ingestion.schema.json`
- `skills/tax-compliance-review/schemas/compliance_review.schema.json`
- `skills/tax-app-builder/schemas/app_config.schema.json`

## Required behaviour

1. Locate schema files.
2. Locate examples, fixtures, and latest generated outputs.
3. Run existing validator scripts where available.
4. If a validator is missing, create one in the relevant skill `scripts/` folder or backend test utilities.
5. Report invalid files with exact field paths and error messages.
6. Do not loosen a schema to hide invalid output unless there is a documented product reason.

## Output expected

Return:

- schema versions checked
- files checked
- pass/fail result
- invalid field paths, if any
- recommended fixes
- tests run

## Guardrails

- Schema changes require example updates.
- Persisted schema changes may require migrations.
- API schema changes require backend and frontend type updates.
