# Classification Taxonomy

Use these stable category identifiers in app logic, database storage, and JSON outputs.

## Item Types

- `income`
- `deduction`
- `non_claimable`
- `needs_review`
- `out_of_scope`

## Income Categories

MVP:
- `salary_wages`
- `allowance`
- `bank_interest`
- `dividend`
- `government_payment`
- `other_income`
- `unknown_income`

Future or specialist review:
- `foreign_income`
- `business_income`
- `rental_income`
- `capital_gain`
- `crypto_gain`
- `trust_distribution`

## Deduction Categories

MVP:
- `work_related_car_expense`
- `work_related_travel_expense`
- `work_related_clothing_laundry`
- `work_related_self_education`
- `work_from_home`
- `tools_equipment`
- `union_fee`
- `professional_membership_fee`
- `donation`
- `tax_agent_fee`
- `income_protection`
- `other_deduction`
- `unknown_deduction`

## Review / Exclusion Categories

- `personal_expense`
- `private_or_mixed_use`
- `insufficient_evidence`
- `duplicate_document`
- `reimbursed_or_potential_double_dip`
- `out_of_scope`
- `needs_review`

## Evidence Status

- `complete`: key fields and source evidence are present
- `partial`: some evidence exists but one or more important fields are missing
- `missing_or_incomplete`: no reliable written evidence or insufficient extracted information

## Risk Levels

- `low`: clear document, routine category, evidence appears complete
- `medium`: likely category but partial evidence or work/private split needs confirmation
- `high`: large amount, unclear nexus, possible reimbursement, duplicated receipt, edited document, out-of-scope signal, or common review risk

## Review Status

- `auto_classified`: low-risk classification suitable for user review queue
- `needs_user_review`: user must confirm facts, work use, reimbursement, or missing evidence
- `needs_tax_agent_review`: complexity or risk requires professional review
