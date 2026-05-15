# /new-migration

Use this command when creating or reviewing a database migration.

## Task

Create an Alembic migration that follows the project database compatibility rules.

## Required behaviour

1. Inspect SQLAlchemy models and current Alembic head.
2. Confirm whether the change affects SQLite, PostgreSQL, or both.
3. Generate a focused migration with a clear name.
4. Avoid database-specific SQL unless justified and isolated.
5. Include downgrade logic where practical.
6. Update tests or fixtures affected by the schema change.
7. Update documentation if canonical table names or status values change.

## Naming convention

Use clear migration names:

```bash
make new-migration name="add_document_status"
```

## Output expected

Return:

- migration file path
- tables/columns changed
- compatibility notes for SQLite/PostgreSQL
- downgrade support status
- tests run

## Guardrails

- Do not rename canonical tables without an ADR.
- Do not remove persisted user data without explicit approval.
- Do not silently change enum/status values without migration and tests.
