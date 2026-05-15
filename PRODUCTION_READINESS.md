# Production Readiness Checklist

Use this checklist before public release.

## Product boundary

- [ ] UI says this is a tax-ready data generator, not a tax agent.
- [ ] No screen says final, guaranteed, ATO-approved, or lodge now.
- [ ] Export says ready for human/tax-agent review, not ready to lodge.

## Security and privacy

- [ ] Raw document text is not written to logs.
- [ ] Sensitive fields are redacted in errors and debug output.
- [ ] AI provider usage is explicit and configurable.
- [ ] Telemetry is off by default for local editions.
- [ ] Users can delete local data.
- [ ] Export requires explicit user action.

## Architecture

- [ ] AI provider calls go through adapter interface.
- [ ] Storage goes through storage adapter.
- [ ] DB access uses SQLAlchemy/repository boundaries.
- [ ] SQLite and PostgreSQL compatibility is maintained where applicable.
- [ ] Long-running workflows are job-safe.

## Data model

- [ ] Documents, extracted items, classification results, and review actions are separate.
- [ ] User-confirmed values do not destroy AI-inferred values.
- [ ] Audit events are written for important state changes.
- [ ] Schema versions are stored with generated outputs.

## Verification

- [ ] `make verify` exists.
- [ ] Backend tests pass.
- [ ] Frontend tests/build pass if frontend exists.
- [ ] JSON schema validators pass.
- [ ] Alembic migrations are checked when DB changed.
- [ ] Demo seed uses synthetic data only.
