---
name: tax-compliance-review
description: Use this skill when reviewing classified Australian individual tax items for evidence completeness, risk, missing fields, human confirmation, tax-agent review triggers, unresolved questions, and export readiness. This skill produces review reports and does not provide final tax advice or lodge returns.
---

# Tax Compliance Review Skill

## Objective

Review classified tax-ready data before export.

This skill checks whether candidate income and deduction items have enough evidence, user confirmation, auditability, and risk handling to be included in a tax-ready review package.

## Responsibility Boundary

This skill is responsible for:

- evidence completeness review
- risk review
- missing field checks
- user-confirmation checks
- tax-agent review triggers
- duplicate and reimbursement risk checks
- export-readiness assessment
- review report generation

This skill is not responsible for:

- final tax advice
- final tax return preparation
- lodgement
- calculating guaranteed refund outcomes
- overriding user or registered tax agent decisions

## Review Philosophy

Be conservative.

When evidence is unclear, mark the item for review rather than approving it.

Use these phrases:

- candidate deduction
- likely category
- requires review
- evidence incomplete
- tax-agent review suggested
- export-ready for human review

Avoid these phrases:

- guaranteed deductible
- ATO approved
- final claim
- lodge now
- refund guaranteed

## Review Inputs

Expected inputs:

- tax session
- ingested documents
- extracted items
- classification results
- source evidence
- user confirmations
- audit events
- duplicate flags
- reimbursement answers

## Review Status Values

Use these review statuses:

- `not_started`
- `needs_user_review`
- `needs_tax_agent_review`
- `evidence_incomplete`
- `user_confirmed`
- `excluded_by_user`
- `ready_for_export`

## Evidence Completeness Checks

For each deduction candidate, check:

- amount exists
- date exists
- supplier/source exists where applicable
- description exists
- original document exists
- source evidence snippet or reference exists
- work-related nexus is explained
- private-use percentage is captured if mixed use
- reimbursement status is known
- duplicate status is resolved
- user confirmation exists for medium/high-risk items

If a required value is missing, do not mark export-ready.

## Income Completeness Checks

For income items, check:

- income type is known or marked unknown
- amount exists
- payer/source exists where available
- date or financial year is known
- source document exists
- out-of-scope income is flagged

## Tax-Agent Review Triggers

Mark `needs_tax_agent_review` when any of these are detected:

- business or sole trader income
- ABN income treated as personal employee income
- BAS/GST language
- rental income or rental schedule
- capital gains or share disposal
- crypto exchange records
- foreign income
- trust distribution
- unusually large deduction
- repeated high-risk claims
- unclear employer reimbursement
- user asks for final tax advice

## Risk Scoring

Risk levels:

### Low

- evidence complete
- ordinary category
- clear source
- user confirmation not required or already captured

### Medium

- evidence partial
- private/work split unclear
- category likely but uncertain
- user confirmation required

### High

- evidence missing
- possible duplicate unresolved
- possible reimbursement
- complex/out-of-scope trigger
- significant amount
- possible legal/tax-agent boundary issue

## Export Readiness Rules

A tax session is export-ready only when:

- no high-risk item is unresolved
- all medium-risk items have user confirmation or clear review notes
- all candidate deductions have evidence status reviewed
- duplicate flags are resolved or clearly excluded
- missing critical fields are either fixed or explicitly documented
- unresolved questions are included in the report

Export-ready means ready for human/tax-agent review, not ready to lodge.

## Report Output

Generate reports using `templates/review_report.md`.

Reports must include:

- session summary
- total documents reviewed
- total candidate income items
- total candidate deduction items
- evidence-complete count
- evidence-incomplete count
- risk distribution
- unresolved questions
- items needing user review
- items needing tax-agent review
- excluded/non-claimable items
- export-readiness decision
- disclaimer

## Output Contract

Review results should validate against `schemas/compliance_review.schema.json`.

## UI Recommendations

High-risk items:

- show red/warning styling
- require explicit user action
- show source evidence
- show reason for review

Medium-risk items:

- show amber/review styling
- ask targeted user questions

Low-risk items:

- allow inclusion in export package but still indicate human review is required

## Failure Behaviour

If review cannot be completed because required data is missing:

- do not fabricate values
- mark session as `not_export_ready`
- list missing inputs
- generate remediation tasks
