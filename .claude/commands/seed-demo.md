# /seed-demo

Use this command to create or verify deterministic demo data.

## Task

Seed the application with safe, synthetic demo data that demonstrates the document ingestion, classification, review, and export workflow.

## Required behaviour

1. Use fake taxpayers, fake employers, fake receipts, and fake amounts.
2. Include at least:
   - one salary/wages income item
   - one bank interest item
   - one low-risk candidate deduction
   - one mixed-use candidate deduction
   - one duplicate-document scenario
   - one out-of-scope or specialist-review scenario
3. Ensure seed output is deterministic.
4. Ensure seeded classifications validate against the schema.
5. Avoid real personal information.

## Output expected

Return:

- seed command run
- sessions created
- documents created
- classification examples created
- schema validation status
- reset instructions

## Guardrails

- Do not include real ABNs, TFNs, addresses, or personal documents.
- Do not seed data that looks like a real taxpayer record.
