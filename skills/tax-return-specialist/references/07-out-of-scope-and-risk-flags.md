# Out-of-Scope and Risk Flags

## Hard Out-of-Scope Signals

Flag `out_of_scope_or_needs_specialist_review` when documents contain:
- BAS
- GST reporting
- ABN income that appears to be business income
- business invoices issued by the user
- sole trader profit and loss reports
- rental property schedules
- crypto exchange CSVs
- share disposal statements
- trust distribution statements
- partnership statements
- SMSF documents
- company financial statements
- foreign income statements

## High-Risk Signals

Set `risk_level` to `high` when:
- amount is large and category is uncertain
- no receipt or written evidence exists for a significant claim
- work/private split is unclear
- possible reimbursement is detected
- duplicated receipt or duplicate bank transaction is detected
- document appears edited or inconsistent
- category commonly requires strong substantiation
- user is asking the system to maximise claims without evidence

## Medium-Risk Signals

Set `risk_level` to `medium` when:
- source evidence is partial
- supplier is unclear
- description is vague
- category is likely but not certain
- work-use percentage is missing
- amount/date is missing but recoverable from context

## Low-Risk Signals

Set `risk_level` to `low` when:
- routine category
- clear supplier, amount, date, and description
- evidence appears complete
- no private-use or reimbursement signal

## Double-Dip / Reimbursement Handling

If the item may have been reimbursed or covered by an allowance:
- category: `reimbursed_or_potential_double_dip` if reimbursement is likely
- otherwise keep likely category but set medium/high risk
- ask: `Were you reimbursed by your employer or another party?`
