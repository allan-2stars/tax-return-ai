# Product Vision v2 — Tax Return AI

## Product identity
- Product name: Tax Return AI
- Product type: Local-first Australian tax evidence review and encrypted review-pack generator
- Positioning: A privacy-preserving assistant for preparing tax evidence for human review, not tax lodgement automation

## Explicit non-goals
- Not tax lodgement software
- Not a registered tax agent replacement
- Not automatic final tax return submission

## Target user
- Australian individual taxpayer
- PAYG employee
- Simple deductions profile
- Wants organized evidence for personal or tax-agent human review

## Core workflow
`login/unlock -> select tax year -> upload documents -> extract text -> classify evidence -> review items -> resolve issues -> export encrypted review pack`

## Problem statement
Australian individuals need a reliable way to organize tax evidence, trace each extracted item back to source documents, and produce a secure review pack. Current tools either optimize for filing automation or weakly protect sensitive files.

## Value proposition
- Privacy first: local-first data handling and conservative cloud behavior
- Review first: every inferred item remains a candidate until user-confirmed
- Evidence first: every item can be traced to source page/snippet
- Export first: generate a portable encrypted review pack for human verification

## MVP scope
- Single-user local workspace with unlock flow
- Tax-year workspace and session management
- Document upload and extraction/classification pipeline (existing scaffold)
- Review queue with explicit statuses and issue resolution
- Encrypted review-pack export as the default output
- Audit visibility for all sensitive actions

## MVP success criteria
- User can complete end-to-end workflow without technical intervention
- 100% of exported items have source traceability (document/page/snippet where available)
- Export is encrypted by default and downloadable in one guided flow
- No external AI calls unless explicitly enabled and consented
- Sensitive data is encrypted at rest by product design target
- User can clearly distinguish unresolved vs review-ready evidence

## Privacy principles
- Local-first by default for storage and processing
- Data minimization: keep only what is required for review workflow
- Least disclosure: no external transmission by default
- Confidential-by-design UX language and defaults
- Explicit retention/deletion policy design with audit trails

## AI usage principles
- AI output is advisory, never final tax advice
- Classification output remains candidate evidence until user review
- Cloud AI is opt-in with explicit consent and visible indicators
- Raw document content is not sent externally by default
- AI unavailability must degrade to safe review workflows, not silent failure

## Product boundaries and compliance posture
- The product prepares evidence and review artifacts only
- Final tax judgments remain with the user and/or a registered tax agent
- UI and documentation must consistently state non-lodgement boundaries
