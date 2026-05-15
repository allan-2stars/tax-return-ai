---
name: tax-app-builder
description: Use this skill when designing, building, refactoring, testing, or reviewing the application architecture for Tax Return AI. Covers FastAPI, Next.js, SQLAlchemy, SQLite/PostgreSQL compatibility, job queues, audit logs, review workflow, export packages, deployment modes, and adapter boundaries. This skill enforces product-ready extensibility and avoids vendor/database/storage lock-in.
---

# Tax App Builder Skill

## Objective

Build an extensible, public-release-ready tax-ready data generator application.

The application must support:

- local-first personal usage
- Docker self-hosted usage
- future desktop packaging
- future multi-user/team deployment
- future tax-agent handoff workflows

It must not be designed as an automatic lodgement system.

## Core Product Positioning

The product is a tax-ready data generator and evidence review assistant.

It helps users organise documents, classify tax-relevant records, review evidence, and export a package for human or tax-agent review.

Avoid product language implying:

- registered tax agent service
- automatic lodgement
- guaranteed refund calculation
- final tax advice
- ATO approval

## Recommended Stack

Default stack:

- Frontend: Next.js + TypeScript
- Backend: FastAPI
- Validation: Pydantic v2
- ORM: SQLAlchemy 2.0
- Migrations: Alembic
- Default DB: SQLite
- Production/team DB: PostgreSQL
- Storage: local filesystem via storage adapter
- Future storage: S3-compatible adapter
- AI: provider adapter, never direct vendor coupling
- Tests: pytest for backend, frontend test runner for UI
- Deployment: Docker Compose first

## Non-Negotiable Adapter Rules

Never design business logic that depends directly on one AI vendor, one database engine, or one storage backend.

Use adapters for:

- AI provider
- database/repository access
- file storage
- OCR provider
- export renderer
- notification delivery

## Edition Model

Design for these editions:

### Personal Local Edition

- single-user
- SQLite
- local file storage
- manual export
- local Docker or desktop mode

### Pro Local Edition

- single-user or household use
- stronger batch processing
- more export templates
- better review workflow

### Team / Tax Agent Edition

- PostgreSQL
- multi-user
- role-based access
- client workspaces
- S3-compatible storage
- audit logs
- review assignment

Do not implement all editions on day one, but avoid decisions that block them.

## Canonical Domain Model

Use these conceptual entities unless the project already defines updated names:

- TaxSession
- Document
- DocumentPage
- ExtractedItem
- ClassificationResult
- ReviewAction
- AuditEvent
- ExportPackage
- AiRun
- AppSetting
- User
- Workspace

MVP may omit `User` and `Workspace` if single-user local mode is active, but schema and service naming should not prevent adding them later.

## Canonical Table Names

Preferred table names:

- `tax_sessions`
- `documents`
- `document_pages`
- `extracted_items`
- `classification_results`
- `review_actions`
- `audit_events`
- `export_packages`
- `ai_runs`
- `app_settings`
- `users`
- `workspaces`

## Backend Structure

Recommended layout:

```text
backend/
  app/
    main.py
    api/
      routes/
    core/
      config.py
      security.py
    db/
      base.py
      session.py
      models/
      migrations/
    schemas/
    services/
      ingestion/
      classification/
      compliance_review/
      export/
      audit/
      ai/
      storage/
    repositories/
    tests/
```

## Frontend Structure

Recommended layout:

```text
frontend/
  app/
  components/
  features/
    upload/
    documents/
    review/
    export/
    settings/
  lib/
    api/
    types/
  tests/
```

## API Design Rules

Prefer resource-oriented APIs:

- `POST /api/tax-sessions`
- `GET /api/tax-sessions/{id}`
- `POST /api/tax-sessions/{id}/documents`
- `GET /api/documents/{id}`
- `POST /api/documents/{id}/extract`
- `POST /api/documents/{id}/classify`
- `GET /api/tax-sessions/{id}/review-queue`
- `POST /api/review-actions`
- `POST /api/tax-sessions/{id}/exports`

Long-running jobs should return job/status IDs rather than blocking the UI.

## Job Queue Strategy

MVP:

- FastAPI background tasks or a simple internal worker

Public/team mode:

- Redis + RQ/Celery/Arq or equivalent queue

Rules:

- ingestion, OCR, classification, and export generation should be job-friendly
- job status must be persisted
- failed jobs must include failure reason
- retry behaviour must be explicit

## Audit Rules

All important changes must write an audit event:

- upload created
- extraction completed/failed
- classification completed/failed
- user edited value
- user confirmed item
- review status changed
- export package generated
- settings changed

Never silently overwrite user-confirmed data.

## Export Package Rules

Export packages should be reproducible and auditable.

A package may include:

- tax-ready summary JSON
- review report Markdown/PDF
- evidence checklist
- source document manifest
- classified item CSV
- unresolved questions list

Never label an export as final lodged tax return.

## Testing Requirements

Before claiming work is complete, run available verification commands:

- backend tests
- frontend tests if changed
- schema validation
- migrations check if DB changed
- lint/build if configured

If tests cannot run, state exactly why.

## Migration Rules

For DB changes:

- use Alembic
- include downgrade where practical
- avoid SQLite-incompatible PostgreSQL-only types in shared models
- include migration tests or at least schema inspection
- do not edit old migrations unless project policy allows it

## Public Release Rules

Product must be easy to deploy across:

- local Docker Compose
- desktop wrapper later
- VPS/self-hosted deployment
- future managed SaaS

Keep environment configuration explicit and documented.
