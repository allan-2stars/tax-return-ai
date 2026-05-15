# /export-package

Use this command when generating or testing a tax-ready evidence package.

## Task

Create a reproducible export package for a tax session after compliance review.

## Required behaviour

1. Confirm compliance review has run.
2. Confirm unresolved high-risk items are clearly listed.
3. Include classified items, evidence manifest, unresolved questions, review report, and source document references.
4. Preserve auditability: include schema versions and generation timestamp.
5. Use the export service/renderer adapter, not direct filesystem assumptions.
6. Store export metadata in `export_packages`.
7. Record an audit event.

## Output expected

Return:

- export package ID
- files included
- unresolved items included
- storage URI
- schema versions
- tests run

## Guardrails

- Do not label the package as a lodged or final tax return.
- Do not exclude unresolved questions from the package.
- Do not include raw sensitive data in logs.
