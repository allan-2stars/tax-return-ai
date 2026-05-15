# /review-queue

Use this command to inspect or improve the review queue workflow.

## Task

Summarise the current tax review queue and identify items that need user or tax-agent review.

## Required behaviour

1. Query classification results grouped by tax session.
2. Prioritise high-risk and low-confidence items.
3. Surface missing evidence and suggested user questions.
4. Keep AI-inferred and user-confirmed values distinct.
5. Confirm the UI does not use final tax advice wording.

## Output expected

Return:

- total items reviewed
- high-risk count
- medium-risk count
- missing evidence count
- needs-user-review count
- needs-tax-agent-review count
- recommended next actions
- tests run or inspection method

## Guardrails

- Do not auto-confirm review items.
- Do not hide high-risk items.
- Do not replace user-confirmed data without audit events.
