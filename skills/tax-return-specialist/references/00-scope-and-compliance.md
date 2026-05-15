# Scope and Compliance

## Product Scope

This skill supports an Australian individual tax-ready data generator for salary and wage earners.

Primary user:
- Australian individual taxpayer
- employee / salary earner
- basic personal income and deduction records

The app prepares a structured review package. It does not lodge a tax return and does not replace professional judgement.

## In Scope for MVP

Income:
- salary and wages
- allowances
- bank interest
- dividends as a document category only, with review if complexity appears
- government payments as a document category only, with review if uncertainty appears

Deductions:
- work-related car expenses
- work-related travel expenses
- work-related clothing and laundry
- work-related self-education
- work-from-home expenses
- tools and equipment
- union or professional association fees
- gifts and donations
- tax agent fees
- income protection insurance
- other candidate deductions requiring review

## Out of Scope or Specialist Review

Flag as `out_of_scope_or_needs_specialist_review` when the source suggests:
- sole trader or business income
- ABN-based income not clearly employment-related
- BAS, GST, PAYG instalments, business activity statements
- rental property schedules
- capital gains tax events
- crypto exchange transactions
- share disposals or complex investments
- foreign income
- trust distribution statements
- partnership, company, SMSF, or trust entities
- employment termination payments requiring detailed treatment
- complex Medicare levy, offsets, HELP, or family tax situations

## Compliance Positioning

The app must not claim to provide tax, legal, or financial advice.

All outputs must be framed as:
- candidate classifications
- likely categories
- preliminary analysis
- evidence review prompts
- tax-ready summaries for human review

Never use finalising language such as:
- guaranteed deductible
- ATO-approved
- ready to lodge
- final refund
- automatic submission

## Conservative Default

If the model is uncertain:
1. mark `needs_review`
2. lower confidence
3. explain uncertainty
4. ask a targeted question
5. avoid final conclusions
