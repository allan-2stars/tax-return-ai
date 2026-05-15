# ADR 001: Use adapter boundaries for AI, database, and storage

Date: 2026-05-12

Status: Accepted

## Context

The product must be usable as a local-first personal app, Docker self-hosted app, future team/tax-agent edition, and possible SaaS product. These deployment modes have different requirements for AI providers, databases, and file storage.

Hard-coding Anthropic, SQLite-only logic, or local filesystem-only storage would make the MVP faster but would create migration pain later.

## Decision

Use explicit adapter boundaries for:

1. AI providers
2. database access patterns
3. file/object storage

Business logic must depend on project-defined interfaces, not vendor SDKs or backend-specific assumptions.

## Consequences

Benefits:

- easier provider switching
- easier public deployment
- easier SaaS/team migration
- easier local testing
- lower vendor lock-in

Costs:

- slightly more initial structure
- more boilerplate
- more tests required around interfaces

## Implementation notes

AI providers should live behind an interface such as:

```text
backend/app/services/ai/base.py
backend/app/services/ai/providers/anthropic.py
backend/app/services/ai/providers/openai.py
backend/app/services/ai/providers/deepseek.py
```

Storage providers should live behind an interface such as:

```text
backend/app/services/storage/base.py
backend/app/services/storage/local.py
backend/app/services/storage/s3.py
```

Database portability should be maintained through SQLAlchemy 2.0 and Alembic migrations.
