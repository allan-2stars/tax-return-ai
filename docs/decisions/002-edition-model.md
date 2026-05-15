# ADR 002: Support local-first, self-hosted, team, and SaaS edition paths

Date: 2026-05-12

Status: Accepted

## Context

The initial developer workflow may run on a Raspberry Pi or local Docker Compose. However, the product is intended for public download and may later become a professional or hosted product.

A purely local MVP would be easy to build but could block future growth. A full SaaS architecture from day one would slow development and increase operational complexity.

## Decision

Design the product around edition targets:

1. `personal-local`
2. `self-hosted`
3. `team-tax-agent`
4. `saas`

The MVP targets `personal-local`, but architecture must not block the other editions.

## Consequences

Benefits:

- fast MVP path
- public-download readiness
- clear upgrade path
- better deployment flexibility

Costs:

- requires discipline around schema design
- requires adapter boundaries
- requires clearer configuration

## Edition defaults

| Edition | DB | Storage | Users | Deployment |
|---|---|---|---|---|
| personal-local | SQLite | Local filesystem | Single user | Docker/local desktop |
| self-hosted | SQLite or PostgreSQL | Local or S3-compatible | Single/small team | Docker Compose |
| team-tax-agent | PostgreSQL | S3-compatible | Multi-user | Server deployment |
| saas | PostgreSQL | S3-compatible | Multi-tenant | Managed cloud |

## Product rule

Features may be edition-gated, but data model changes should be designed with future compatibility in mind.
