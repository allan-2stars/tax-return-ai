# Tax-Ready Review Report

## Session Summary

- Tax session: {{ tax_session_id }}
- Generated at: {{ generated_at }}
- Review status: {{ review_status }}
- Export readiness: {{ export_readiness.status }}

## Important Notice

This report organises tax-related information for human review. It is not final tax advice, not a registered tax agent service, and not a lodged tax return.

## Summary

- Documents reviewed: {{ summary.documents_reviewed }}
- Candidate income items: {{ summary.income_items }}
- Candidate deduction items: {{ summary.deduction_items }}
- Evidence complete: {{ summary.evidence_complete }}
- Evidence incomplete: {{ summary.evidence_incomplete }}

## Risk Distribution

- Low: {{ summary.risk_counts.low }}
- Medium: {{ summary.risk_counts.medium }}
- High: {{ summary.risk_counts.high }}

## Items Requiring User Review

{{ user_review_items }}

## Items Requiring Tax-Agent Review

{{ tax_agent_review_items }}

## Unresolved Questions

{{ unresolved_questions }}

## Export Readiness Decision

{{ export_readiness.reason }}
