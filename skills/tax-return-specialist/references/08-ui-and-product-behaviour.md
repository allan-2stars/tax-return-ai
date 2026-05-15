# UI and Product Behaviour

## User-Facing Positioning

Display a persistent disclaimer:

This tool helps organise tax information and prepare a review package. It does not provide final tax advice and does not replace review by the user or a registered tax agent.

## Review Queue

Create review queues for:
- high-risk items
- low-confidence items
- missing evidence
- out-of-scope items
- duplicate candidates
- mixed-use deductions
- possible reimbursement/double-dip items

## Risk Visuals

Recommended visual hierarchy:
- high: strong warning treatment
- medium: amber/orange review treatment
- low: neutral/subtle treatment

Do not hide high-risk items inside collapsed sections by default.

## Evidence Panel

For each item, show:
- original filename
- document preview
- OCR snippet
- amount/date/supplier extracted
- confidence
- missing fields
- suggested user questions
- review status

## User Confirmation

When the user confirms a field:
- mark field as user-confirmed
- preserve previous AI-inferred value in audit history
- store timestamp
- allow later correction

## Export Package

A tax-ready export should include:
- item summary
- category
- amount
- evidence status
- review status
- risk level
- source document reference
- unresolved questions
- out-of-scope warnings

Never label export as final lodgement data unless reviewed and confirmed by the appropriate human workflow.
