# Income Categories

## General Rule

Classify income conservatively. If the document indicates income but the type is unclear, use `unknown_income` and mark `needs_user_review`.

## salary_wages

Use for:
- income statements
- PAYG summaries
- payslips
- salary and wage records

Common source signals:
- employer name
- gross payments
- PAYG withholding
- STP income statement
- payroll terms

## allowance

Use for:
- employer-paid allowances
- travel allowance
- laundry allowance
- car allowance
- meal allowance
- tool allowance

Important behaviour:
- An allowance does not automatically make a related expense claimable.
- If an expense appears related to an allowance, still check evidence, nexus, and reimbursement/double-dip risk.

## bank_interest

Use for:
- bank interest statements
- savings account annual interest summaries

## dividend

Use for:
- dividend statements
- managed fund dividend-like income only as preliminary classification

Escalate to review when:
- franking credits appear
- dividend reinvestment appears
- foreign tax credits appear
- managed fund distributions appear complex

## government_payment

Use for:
- Centrelink or Services Australia payment summaries
- taxable government benefit statements

Escalate when tax treatment is unclear.

## other_income / unknown_income

Use when:
- income exists but does not fit an MVP category
- description is ambiguous
- source is incomplete

Set `review_status` to `needs_user_review` or `needs_tax_agent_review` depending on complexity.
