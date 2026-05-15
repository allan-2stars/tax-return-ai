# tax-return-ai

Australian individual **tax-ready data generator** — upload bank/income PDFs, auto-classify items via AI, review and approve, and export a structured package for yourself or your tax agent.

> ⚠️ This tool organises tax information and prepares a review package. It does **not** provide final tax advice, lodge tax returns, or replace a registered tax agent.

---

## Features

- **Upload documents** — drag-drop multi-file upload (PDF/PNG/JPG/TIFF, up to 20MB each, 20 files per batch)
- **AI classification** — auto-detect income vs deduction items with confidence scores and ATO reference hints
- **Review workflow** — approve, flag for review, edit amounts/descriptions inline
- **Compliance dashboard** — risk heatmap (low/medium/high), evidence status, tax agent triggers
- **Export** — JSON or CSV exports with itemised summaries, persisted export history
- **Batch operations** — bulk upload, bulk review approve/flag
- **Health & monitoring** — structured logging with request IDs, job status tracking, rate limiting
- **Architecture** — adapter pattern across AI, OCR, storage, and database backends

---

## Quick Start (Development)

```bash
# Clone and enter
git clone <repo-url> && cd tax-return-ai

# Configure environment
cp .env.example .env
# Edit AI_PROVIDER=mock (no API keys needed for dev)

# Start all services (SQLite dev mode)
make up

# Check backend health
curl http://localhost:8010/api/health

# Open the app
open http://localhost:3020

# Follow logs
make logs

# Stop everything
make down
```

Default dev config uses:
- **SQLite** — database stored in `./data/taxapp.db`
- **Mock AI provider** — no API keys required, returns deterministic classifications
- **Mock OCR provider** — no external dependencies
- **Personal edition** — single-user, no auth

---

## Production Deployment

### Prerequisites

- Docker & Docker Compose v2 on the target machine
- Cloudflare Tunnel (`cloudflared`) or alternative reverse proxy
- (Optional) PostgreSQL if using team edition

### Setup

```bash
# 1. Clone the repo on the production machine
git clone <repo-url> /opt/tax-return-ai && cd /opt/tax-return-ai

# 2. Configure environment
cp .env.example .env
# Set real values:
#   AI_PROVIDER=claude or openai
#   ANTHROPIC_API_KEY=sk-...
#   DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/taxapp
#   EDITION=team (for PostgreSQL + S3 storage)

# 3. Build and start
docker compose up -d --build

# 4. Run database migrations
make migrate

# 5. Verify health
curl http://localhost:8010/api/health
# Expected: {"status":"ok","version":"1.0.0","database":"connected"}
```

### Cloudflare Tunnel Setup

Create a tunnel pointing to the Docker host:

| Subdomain | Target |
|---|---|
| `tax.signpega.com` | `localhost:3020` (frontend) |
| `tax-api.signpega.com` | `localhost:8010` (backend) |

The backend includes built-in CORS for these origins. Frontend uses `NEXT_PUBLIC_API_URL` env var to point at the API tunnel URL.

### Deployment Script

```bash
# Full deploy with pre-flight checks, build, migrate, and health verification
./scripts/deploy.sh

# Which does:
#   1. git pull (latest code)
#   2. docker compose down && docker compose up -d --build
#   3. alembic upgrade head
#   4. Health check (waits up to 60s)
#   5. Post-deploy database backup
```

### Database Backups

```bash
# Manual backup
./scripts/backup.sh

# Automatic — add to crontab (runs daily at 02:00)
0 2 * * * cd /opt/tax-return-ai && ./scripts/backup.sh
```

Backups go to `./backups/` with 7-day retention.

### Rolling Back

```bash
# 1. Checkout the previous version
git checkout <previous-tag-or-commit>

# 2. Rebuild and restart
docker compose up -d --build

# 3. Re-run migrations (if needed)
make migrate
```

---

## Architecture

```
┌──────────────┐       ┌──────────────────┐        ┌──────────────┐
│   Frontend   │──────▶│    Backend        │───────▶│  Database     │
│  Next.js 14  │       │   FastAPI/Python  │        │ SQLite/PG     │
│  localhost:3020 │     │   localhost:8010  │        └──────────────┘
│  tax.sign... │       │  tax-api.sign...  │              ▲
└──────────────┘       └─────────┬────────┘              │
                                  │                      │
                                  ▼                      │
                        ┌──────────────────┐             │
                        │   AI Provider     │─────────────┘
                        │  (mock/Anthropic/ │
                        │   OpenAI)         │
                        └──────────────────┘
                                  │
                                  ▼
                        ┌──────────────────┐
                        │   OCR Provider    │
                        │ (mock/pdfplumber/ │
                        │   tesseract)      │
                        └──────────────────┘
```

### Backend Structure

```
app/
├── ai/              # AI provider adapters (mock, anthropic, openai)
├── constants/       # Tax categories, risk enums, FY helpers
├── db/              # Database session and base
├── models/          # SQLAlchemy ORM models
├── ocr/             # OCR provider adapters (mock, pdfplumber)
├── repositories/    # DB queries
├── routers/         # API endpoints (7 routers)
├── schemas/         # Pydantic request/response models
├── services/        # Business logic (ingestion, classification, compliance)
├── storage/         # Storage adapters (local, S3)
└── utils/           # Sanitization, logging helpers
```

### Design Principles

1. **Adapter pattern** — AI, OCR, storage, and database all behind interfaces; swap providers via config
2. **Local-first** — SQLite default, zero external services required for dev
3. **Review-first** — All AI output is *candidate* classification only; user must review
4. **Auditability** — Every state change writes an audit event with timestamp and details
5. **Privacy** — Telemetry off by default, sensitive data never logged (configurable redaction)

---

## API Reference

All endpoints are prefixed with `/api`. Swagger docs available at `http://localhost:8010/docs`.

### Health

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Health check (status, version, DB connection) |

### Sessions

| Method | Path | Description |
|---|---|---|
| GET | `/api/sessions` | List all sessions (newest first) |
| POST | `/api/sessions` | Create session |
| GET | `/api/sessions/{id}` | Get session by ID |
| PATCH | `/api/sessions/{id}` | Update title, notes, or status |
| DELETE | `/api/sessions/{id}` | Delete session and all related data |
| GET | `/api/sessions/{id}/stats` | Document/item counts for a session |

### Documents

| Method | Path | Description |
|---|---|---|
| GET | `/api/documents?session_id=` | List documents in a session |
| POST | `/api/documents/upload` | Upload single document (multipart) |
| POST | `/api/documents/upload/batch` | Upload up to 20 files (multipart) |
| DELETE | `/api/documents/{id}` | Delete document |
| GET | `/api/documents/{id}/pages` | Get OCR text by page |

### Items / Classification

| Method | Path | Description |
|---|---|---|
| GET | `/api/items?session_id=&needs_review=` | List items (filterable) |
| POST | `/api/items/classify` | Classify a document's text |
| PATCH | `/api/items/{id}` | Update amount/description/category |
| POST | `/api/items/{id}/review` | Toggle review status on single item |
| POST | `/api/items/bulk-review` | Toggle review status on multiple items |
| DELETE | `/api/items/{id}` | Delete item |

### Jobs

| Method | Path | Description |
|---|---|---|
| GET | `/api/jobs?session_id=` | List jobs by session |
| GET | `/api/jobs/{id}/status` | Get job progress/status |

### Compliance

| Method | Path | Description |
|---|---|---|
| GET | `/api/compliance/{session_id}` | Full compliance review with risk heatmap |

### Export

| Method | Path | Description |
|---|---|---|
| GET | `/api/export/{session_id}` | Export as JSON (default) or CSV (`?format=csv`) |
| GET | `/api/export/{session_id}/history` | List previous exports |

### Monitoring

| Method | Path | Description |
|---|---|---|
| GET | `/api/monitoring/jobs/summary` | Job stats by status |

---

## Commands Reference

### Makefile

| Command | Description |
|---|---|
| `make up` | Build and start all Docker services |
| `make down` | Stop all services |
| `make logs` | Follow all logs |
| `make test` | Run backend tests |
| `make test-coverage` | Run backend tests with coverage |
| `make test-frontend` | Run frontend tests |
| `make verify` | Lint + schema validation + tests |
| `make migrate` | Run Alembic migrations |
| `make revision name="..."` | Create autogenerated migration |
| `make seed-demo` | Seed sample data for development |

### Docker Compose

```bash
# Build specific service
docker compose build backend
docker compose build frontend

# View logs for one service
docker compose logs -f backend
docker compose logs -f frontend

# Execute commands inside containers
docker compose exec backend pytest tests/
docker compose exec frontend npm test

# Rebuild and restart (after code changes)
docker compose down && docker compose up -d --build
```

---

## Editions

| Edition | Database | Storage | Auth | Use Case |
|---|---|---|---|---|
| `personal` | SQLite | local | none | Individual, free download |
| `pro` | SQLite | local | none | Paid local upgrade |
| `team` | PostgreSQL | S3 | JWT | Tax agents / firms |

Set via `EDITION` in `.env`.

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `EDITION` | No | `personal` | Edition mode (`personal`/`pro`/`team`) |
| `FINANCIAL_YEAR` | No | `2025-2026` | Default FY for new sessions |
| `AI_PROVIDER` | No | `mock` | AI backend (`mock`/`anthropic`/`openai`) |
| `AI_MODEL` | No | — | Model name override |
| `ANTHROPIC_API_KEY` | Conditional | — | Required if AI_PROVIDER=anthropic |
| `OPENAI_API_KEY` | Conditional | — | Required if AI_PROVIDER=openai |
| `OCR_PROVIDER` | No | `mock` | OCR backend (`mock`/`pdfplumber`/`tesseract`) |
| `DATABASE_URL` | No | SQLite | Database connection string |
| `STORAGE_BACKEND` | No | `local` | Storage backend (`local`/`s3`) |
| `MAX_UPLOAD_SIZE_MB` | No | `20` | Max upload file size |
| `LOG_LEVEL` | No | `INFO` | Python log level |
| `REDACT_SENSITIVE_LOGS` | No | `true` | Strip sensitive data from logs |
| `TELEMETRY_ENABLED` | No | `false` | Anonymous usage telemetry |

---

## Configuration

Copy `.env.example` to `.env` and uncomment/adjust the values you need.

For production with real AI providers, at minimum set:
```
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
OCR_PROVIDER=pdfplumber
```

For team edition with PostgreSQL + S3:
```
EDITION=team
DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/taxapp
STORAGE_BACKEND=s3
AWS_BUCKET=my-taxapp-uploads
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
```
Also un-comment the `db` service and its env vars in `docker-compose.yml`.

---

## Testing

```bash
# Backend tests
make test

# Backend with coverage
make test-coverage

# Frontend tests
make test-frontend

# Full verification suite
make verify
```

Continuous integration via GitHub Actions (`.github/workflows/ci.yml`):
- Ruff linting
- Pytest with PostgreSQL service
- Vitest frontend tests

---

## Project Layout

```
tax-return-ai/
├── app/                  # FastAPI backend
│   ├── ai/              # AI provider adapters
│   ├── constants/       # Tax categories, risk enums, FY helpers
│   ├── db/              # Database session and base
│   ├── models/          # SQLAlchemy ORM models
│   ├── ocr/             # OCR provider adapters
│   ├── repositories/    # DB queries
│   ├── routers/         # API endpoints
│   ├── schemas/         # Pydantic request/response models
│   ├── services/        # Business logic
│   └── storage/         # Storage adapters
├── backend/             # Backend Dockerfile
├── frontend/            # Next.js (App Router)
│   ├── app/             # Pages (home, session/[id])
│   ├── components/      # React components
│   └── lib/             # API client, utilities
├── scripts/             # deploy.sh, backup.sh, seed_demo.py
├── skills/              # Domain skill packs (tax rules, compliance)
├── tests/               # Backend + frontend tests
├── docker-compose.yml   # Service orchestration
├── Makefile             # Dev commands
└── .env.example         # Environment template
```

---

## Security

- **Rate limiting** — 10 uploads/min, 30 session reads/min, 60 general/min (per dependency)
- **File validation** — whitelist PDF/PNG/JPG/TIFF only, max 20MB per file
- **Input sanitization** — HTML sanitization on all user-provided text fields
- **Security headers** — CORS with explicit origins, Content-Type restrictions
- **Audit logging** — every state change recorded with timestamp
- **Privacy** — sensitive data redacted from logs by default

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| "Failed to fetch" on upload | CORS misconfiguration | Check `CORS_ORIGINS` / Cloudflare Tunnel targets match |
| 429 errors | Rate limit hit | Wait 10-60 seconds before retrying |
| Documents stuck "queued" | Background worker not running | Check `docker compose ps` — backend should be up |
| "Multiple rows found" on upload | Old bug (fixed) | Rebuild: `docker compose up -d --build` |
| DB connection errors | PostgreSQL not ready | Wait or add `depends_on` with `condition: service_healthy` |
| Frontend blank on deploy | Wrong `output` in next.config.js | Must be `output: 'standalone'` (not `export`) for SSR |
