---
name: tax-document-ingestion
description: Use this skill when designing, building, testing, or reviewing document ingestion workflows for an Australian tax-ready data generator. Covers upload handling, PDF/image/email/bank statement/receipt ingestion, OCR/text extraction, duplicate detection, field normalisation, missing-field detection, and unified JSON output. This skill does not make final tax conclusions.
---

# Tax Document Ingestion Skill

## Objective

Build and maintain the document ingestion layer for a tax-ready data generator.

This skill converts uploaded files into structured, auditable, normalised document records that can later be classified by `tax-return-specialist` and reviewed by `tax-compliance-review`.

## Responsibility Boundary

This skill is responsible for:

- accepting supported file types
- preserving original files and metadata
- extracting text from PDFs, images, emails, bank statements, and receipts
- detecting document type
- extracting candidate fields
- detecting duplicates
- detecting missing or low-confidence fields
- producing canonical ingestion JSON

This skill is not responsible for:

- deciding whether an item is ultimately claimable
- providing final tax advice
- lodging tax returns
- bypassing human review
- modifying user-confirmed classification data

## Processing Pipeline

Use this pipeline unless the project explicitly defines a different one:

1. Receive upload.
2. Store original file immutably.
3. Calculate file hash.
4. Capture metadata.
5. Extract text layer if available.
6. Use OCR only when text extraction is insufficient.
7. Split multi-document PDFs where possible.
8. Detect document type.
9. Extract candidate fields.
10. Detect duplicates or near-duplicates.
11. Produce normalised ingestion JSON.
12. Mark low-confidence or missing fields for review.

## Supported Document Types

Initial supported types:

- receipt
- tax invoice
- payslip
- income statement
- bank statement
- donation receipt
- membership or union fee receipt
- insurance statement
- work equipment invoice
- email body
- email attachment
- unknown document

Future supported types:

- rental schedule
- share statement
- crypto exchange CSV
- foreign income statement
- business activity statement

Future types must be flagged as `out_of_scope_or_needs_specialist_review` unless the product edition explicitly supports them.

## File Handling Rules

Always preserve:

- original filename
- original file extension
- MIME type
- file size
- SHA-256 hash
- upload timestamp
- source channel
- storage URI
- extracted text
- extraction method
- extraction confidence
- page count if applicable

Never delete duplicates automatically. Mark duplicates and preserve references.

Never overwrite an original file.

## Extraction Rules

Prefer deterministic extraction before AI extraction:

1. PDF text layer extraction.
2. Structured parser when applicable.
3. OCR fallback.
4. AI-assisted extraction only after raw text/image extraction.

For OCR:

- capture OCR confidence where available
- capture page-level text
- preserve uncertain tokens
- do not invent missing values
- mark unreadable sections as `missing_or_unreadable`

## Duplicate Detection

Use several signals:

- exact file hash
- same supplier + date + amount
- highly similar extracted text
- same invoice number
- same payment reference
- same image perceptual hash if available

Duplicate statuses:

- `not_duplicate`
- `possible_duplicate`
- `confirmed_duplicate`

Possible duplicates require user review.

## Canonical Status Values

Document status should use these values:

- `uploaded`
- `stored`
- `text_extracted`
- `ocr_required`
- `ocr_completed`
- `extraction_failed`
- `normalised`
- `duplicate_detected`
- `ready_for_classification`
- `needs_user_review`

## Output Contract

All ingestion output must validate against `schemas/document_ingestion.schema.json`.

## Integration With Other Skills

After ingestion:

- send normalised documents to `tax-return-specialist` for classification
- send classified items to `tax-compliance-review` for evidence and risk review

Do not skip these stages.

## Development Rules

When building code:

- keep parser logic separate from API routes
- keep storage backend behind an adapter
- keep OCR provider behind an adapter
- use background jobs for expensive processing
- record audit events for each processing stage
- provide deterministic tests with sample documents

## Failure Behaviour

If extraction fails:

- preserve original file
- save failure reason
- set status to `extraction_failed`
- create review task
- do not silently discard the document

If a field is uncertain:

- include it with confidence if useful
- mark it as low confidence
- add it to `missing_or_uncertain_fields`
