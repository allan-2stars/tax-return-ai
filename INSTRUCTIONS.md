# Project Instructions

## Product summary

This project builds a local-first, public-downloadable Australian tax document organiser and tax-ready package generator.

The product helps users collect, extract, classify, review, and export tax-relevant information. It must remain review-first and must not be represented as a replacement for a registered tax agent.

## Why this product exists

Most ordinary salary earners do not need a complex tax platform. They need a clean way to:

1. dump documents into one place
2. have the system identify likely tax-relevant items
3. see what evidence is missing
4. resolve ambiguous claims
5. export a clean package for themselves or a registered tax agent

The product value is organisation, classification, review workflow, and handoff quality — not final tax advice.

## Compliance reasoning

The product deliberately avoids lodgement and final advice features.

The Australian Taxation Office states that registered tax agents can prepare and lodge returns and are the only people that can charge a fee for doing so. The Tax Practitioners Board describes tax agent services as including preparing or lodging returns or other documents about a client's liabilities, obligations, or entitlements under taxation law.

This means the product must be designed and worded carefully. It can organise and prepare a review package, but it must not claim to provide final tax-agent services.

## Core positioning

Use:

- tax-ready data generator
- document organiser
- evidence package generator
- candidate classification assistant
- review workflow
- tax-agent handoff package

Avoid:

- AI tax agent
- automatic tax return
- lodge directly
- guaranteed deduction
- refund maximiser
- ATO-approved result

## Architecture philosophy

The project should be easy to run locally but not trapped as a toy local app.

Design every major external dependency behind an adapter:

- AI provider adapter
- database compatibility boundary
- storage adapter

This lets the product evolve across:

- local personal edition
- Docker self-hosted edition
- future professional/team edition
- future SaaS edition

## Edition model

### Personal Local Edition

Target: individual public download.

Default choices:

- SQLite
- local file storage
- local Docker or future desktop wrapper
- single user
- manual export

### Self-hosted Edition

Target: advanced users, small offices, or privacy-conscious users.

Default choices:

- Docker Compose
- SQLite or PostgreSQL
- local or S3-compatible storage
- optional auth

### Team / Tax Agent Edition

Target: future professional workflow.

Default choices:

- PostgreSQL
- S3-compatible storage
- multi-user workspaces
- audit events
- review assignment
- stricter export controls

### SaaS Edition

Target: possible hosted product.

Default choices:

- tenant isolation
- PostgreSQL
- S3-compatible object storage
- provider-managed AI configuration
- stronger security, billing, and compliance review

## Data model principles

Documents and classifications are separate.

A document may contain many pages. A page may produce many extracted items. An extracted item may receive multiple classification runs over time. User-confirmed values override AI-inferred values but should not destroy the audit trail.

Core entities:

- tax session
- document
- document page
- extracted item
- classification result
- review action
- audit event
- export package
- AI run

## AI behaviour principles

The AI should:

- classify conservatively
- surface uncertainty
- ask targeted questions
- preserve evidence links
- avoid final conclusions
- never fabricate thresholds or rules

The AI should not:

- decide final deductibility
- advise final claims
- promise refunds
- submit anything to government systems

## Review workflow principles

High-risk and low-confidence items must be visible.

The UI should make it easy to answer:

- What is this item?
- Why was it classified this way?
- What evidence supports it?
- What is missing?
- Does the user need to confirm anything?
- Should this be referred to a registered tax agent?

## Decision log

Initial decisions:

1. Use adapter pattern for AI, database, and storage.
2. Support local-first personal edition while keeping PostgreSQL/S3/team readiness.
3. Maintain TPB/ATO-safe product positioning: no lodgement and no final tax advice.

Detailed ADRs live in `docs/decisions/`.

## Contributor guidance

When contributing, optimise for:

- correctness over cleverness
- explicit review states
- auditability
- schema stability
- deployability across platforms
- clear product boundary

Do not optimise for:

- one-off demos that bypass architecture
- vendor lock-in
- hidden assumptions
- irreversible AI decisions
- aggressive tax-claim wording
