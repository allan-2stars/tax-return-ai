# ADR 004: Treat tax documents and extracted data as highly sensitive

Date: 2026-05-13

Status: Accepted

## Context

The product stores and analyses tax-related records. These records may include TFNs, addresses, names, employer details, bank details, income amounts, receipts, identity documents, and other sensitive personal information.

A public-downloadable product must be safe by default. Local-first storage helps, but local-first is not enough if logs, telemetry, AI provider calls, exports, or support bundles leak sensitive data.

## Decision

The product will use privacy-preserving defaults:

- local storage by default for personal editions
- explicit user action before export
- no raw document text in application logs
- no silent upload of source documents to external services
- AI provider usage must be explicit and configurable
- telemetry must be opt-in for local/public editions
- deletion/export controls must be visible in the UI

## Consequences

Benefits:

- safer public release posture
- better user trust
- easier future compliance review
- lower risk of accidental sensitive-data exposure

Costs:

- more engineering work around redaction, logging, and provider adapters
- more careful debugging practices
- more explicit settings UI required

## Implementation notes

Sensitive fields should be redacted in logs and test snapshots.

Avoid logging:

- TFNs
- bank account numbers
- residential addresses
- full extracted document text
- original document filenames if they contain names or sensitive details
- AI prompts containing raw user data

Use synthetic fixtures for tests and demos.
