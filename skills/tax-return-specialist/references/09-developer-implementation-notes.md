# Developer Implementation Notes

## Architecture Pattern

Recommended pipeline:

1. Upload document
2. Store original file
3. OCR / text extraction
4. Extract candidate line items
5. Classify with this skill
6. Validate against JSON schema
7. Store raw extraction, AI classification, and audit metadata
8. Present review queue
9. User confirms or corrects
10. Export review package

## Data Storage Rules

Store separately:
- original document metadata
- raw extracted text
- candidate items
- AI analysis output
- user-confirmed fields
- audit events

## Do Not Hard-Code Tax Logic in UI

Keep tax categories, risk rules, and display labels in shared constants or backend configuration.

## Validation

Every AI output must pass schema validation before database insertion.

If validation fails:
- do not discard the source document
- store failure details
- create a `needs_review` item
- surface error to developer logs

## Testing Requirements

Add tests for:
- valid schema output
- missing amount
- missing date
- duplicate receipt
- blurry OCR / low confidence
- out-of-scope ABN business income
- rental property statement detection
- crypto CSV detection
- reimbursed expense detection
- mixed-use work-from-home bill

## Suggested App Models

Core entities:
- `Document`
- `ExtractedText`
- `TaxItem`
- `TaxAnalysis`
- `ReviewQuestion`
- `AuditEvent`
- `ExportPackage`

## Claude/Codex Instruction

When coding, prefer small, testable changes. Update schema, constants, tests, and UI labels together.
