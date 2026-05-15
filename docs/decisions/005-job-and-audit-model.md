# ADR 005: Use persisted jobs and audit events for long-running workflows

Date: 2026-05-13

Status: Accepted

## Context

Document ingestion, OCR, classification, compliance review, and export generation can fail or take time. A public product must show progress, recover from failure, and explain what happened.

## Decision

Long-running workflows must be modelled as persisted jobs and must write audit events.

MVP may use FastAPI background tasks or a simple internal worker, but the domain model should not assume synchronous processing only.

## Required job fields

Recommended table: `jobs`.

Fields:

- `id`
- `tax_session_id`
- `document_id` where relevant
- `job_type`
- `status`
- `progress_percent`
- `attempt_count`
- `max_attempts`
- `failure_reason`
- `created_at`
- `started_at`
- `completed_at`

## Required statuses

- `queued`
- `running`
- `succeeded`
- `failed`
- `cancelled`
- `retrying`

## Consequences

Benefits:

- clearer UX
- resumable processing
- better debugging
- better auditability
- easier upgrade path to Redis/RQ/Celery/Arq later

Costs:

- more schema and service boilerplate
- must handle partial failure states explicitly
