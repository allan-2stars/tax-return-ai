# Recommended Architecture

## Principle

Build a local-first product that can grow into team and SaaS deployments without rewriting the core domain.

## Recommended Deployment Modes

- Personal Docker mode: SQLite + local storage
- Desktop mode: local API + local DB + desktop shell
- Team mode: PostgreSQL + object storage + role-based access
- Future SaaS: managed Postgres + object storage + queue workers

## Core Adapters

- AI provider adapter
- Storage adapter
- OCR adapter
- Export renderer adapter
- Repository layer
