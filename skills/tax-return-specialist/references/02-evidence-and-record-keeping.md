# Evidence and Record Keeping

## Core Evidence Principles

For a candidate deduction, evaluate:

1. Written evidence
   - receipt
   - tax invoice
   - statement
   - employer document
   - payment record

2. Nexus to assessable income
   - why the expense relates to earning employment income
   - whether the expense was incurred while performing work duties

3. Apportionment
   - private percentage
   - work percentage
   - mixed-use explanation

4. Reimbursement
   - whether employer reimbursed the user
   - whether an allowance already covered the expense
   - whether the item risks double counting

## Required Evidence Fields

Capture where possible:
- amount
- date
- supplier or source
- description
- ABN if available on invoice
- payment method if visible
- GST if visible
- document filename
- page number
- OCR raw snippet
- confidence score

## Missing Evidence Handling

Do not automatically reject a candidate deduction when evidence is missing.

Instead:
- set `evidence_status` to `partial` or `missing_or_incomplete`
- add missing fields to `missing_fields`
- add user questions to `suggested_user_questions`
- lower confidence
- set `review_status` to `needs_user_review`

## Duplicate Handling

If duplicate receipts or statements are detected:
- do not delete automatically
- mark the suspected duplicate item as `duplicate_document`
- preserve both document references
- explain why duplication was suspected

Duplicate signals include:
- same supplier
- same amount
- same date
- same invoice number
- near-identical OCR text
- same image hash or file hash

## Multiple Receipts in One Document

If a PDF or image contains multiple receipts:
- split into separate candidate line items when reasonably clear
- preserve the parent document ID
- preserve page and snippet references

## Auditability

Every classification must preserve:
- original filename
- original extracted text or OCR text
- classification reasoning
- confidence score
- analysis timestamp
- model or rule version if available
- user confirmation state

Never overwrite user-confirmed values silently.
