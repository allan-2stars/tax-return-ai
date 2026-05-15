# /compliance-review

Use this command when checking whether a tax session is ready for human/tax-agent review export.

## Task

Run compliance review using `tax-compliance-review`.

## Required behaviour

1. Inspect all classification results for the tax session.
2. Check evidence completeness for every candidate deduction.
3. Check user confirmation for medium/high-risk items.
4. Check duplicate, reimbursement, and mixed-use risks.
5. Identify out-of-scope or specialist-review triggers.
6. Produce a compliance review JSON result.
7. Validate against `skills/tax-compliance-review/schemas/compliance_review.schema.json`.
8. Generate or update the review report template output.

## Output expected

Return:

- export readiness decision
- high/medium/low risk counts
- unresolved evidence issues
- user questions remaining
- tax-agent review triggers
- schema validation result
- tests run

## Guardrails

- Export-ready means ready for human review, not ready to lodge.
- Do not convert candidate deductions into final claims.
- Do not hide unresolved high-risk items.
