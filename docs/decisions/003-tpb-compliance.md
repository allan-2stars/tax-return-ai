# ADR 003: Maintain tax-ready data generator positioning

Date: 2026-05-12

Status: Accepted

## Context

The product deals with Australian tax documents and candidate classifications. This creates legal and compliance risk if the product is framed as a tax agent, final tax advice provider, or automated lodgement service.

Australian guidance distinguishes between general software/document support and tax agent services such as preparing or lodging tax-related documents about a client's liabilities, obligations, or entitlements. The product must avoid claiming or performing final tax-agent functions unless the business model changes and qualified compliance review is completed.

## Decision

The product will be positioned as a:

- tax document organiser
- tax-ready data generator
- candidate classification assistant
- evidence package generator
- review and handoff workflow

The product will not:

- lodge tax returns
- claim to be a registered tax agent
- provide final tax advice
- guarantee claims or refund outcomes
- say output is ATO-approved

## Consequences

Benefits:

- safer public positioning
- clearer UI copy
- easier review-first product design
- reduced risk of accidental overclaiming

Costs:

- cannot market as a full AI tax-return product
- must maintain disclaimers and careful wording
- must keep human review in the workflow

## Required UI wording

The application should show wording similar to:

> This tool helps organise tax information and prepare a review package. It does not provide final tax advice, does not lodge tax returns, and does not replace review by the user or a registered tax agent.

## Required implementation behaviour

- All AI classifications are candidates.
- High-risk or low-confidence items require review.
- Final export must label unresolved items clearly.
- The UI must avoid final advice wording.
