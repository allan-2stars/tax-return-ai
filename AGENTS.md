# CLAUDE.md — tax-return-ai

This file is read automatically by Claude Code every session.
Read it fully before writing any code, creating any file, or running any command.

---

## What This Project Is

**tax-return-ai** — an Australian individual tax-ready data generator and review tool.

Helps salary and wage earners organise tax documents, classify candidate items, surface
missing evidence, and produce a structured review package for themselves or their tax agent.

**Does not** lodge returns, give final tax advice, or guarantee ATO acceptance.
See `docs/decisions/003-tpb-compliance.md` — do not revisit without legal review.

---

## Project Layout

```
tax-return-ai/
├── CLAUDE.md                          ← this file (always loaded)
├── INSTRUCTIONS.md                    ← product context and "why" reasoning
├── PRODUCTION_READINESS.md            ← pre-release checklist
├── Makefile                           ← all dev commands
├── .env.example                       ← all env vars documented
├── pyproject.toml                     ← Python tooling config
├── requirements.txt                   ← pinned backend deps
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
├── app/                               ← FastAPI backend
│   ├── main.py
│   ├── config.py                      ← Pydantic Settings + feature flags
│   ├── ai/
│   │   ├── providers/
│   │   │   ├── base.py                ← AIProvider ABC
│   │   │   ├── anthropic.py
│   │   │   ├── openai.py
│   │   │   └── mock.py
│   │   └── factory.py                 ← get_provider() via AI_PROVIDER env
│   ├── storage/
│   │   ├── base.py                    ← StorageBackend ABC
│   │   ├── local.py
│   │   ├── s3.py
│   │   └── factory.py
│   ├── ocr/
│   │   ├── providers/
│   │   │   ├── base.py                ← OCRProvider ABC
│   │   │   ├── pdfplumber.py
│   │   │   ├── tesseract.py
│   │   │   └── mock.py
│   │   └── factory.py
│   ├── db/
│   │   ├── base.py
│   │   └── session.py
│   ├── models/                        ← SQLAlchemy ORM — use canonical table names below
│   ├── repositories/                  ← ALL DB queries here only
│   ├── services/
│   │   ├── ingestion/
│   │   ├── classification/
│   │   ├── compliance_review/
│   │   ├── export/
│   │   └── audit/
│   ├── routers/
│   ├── schemas/                       ← Pydantic request/response models
│   └── constants/
│       ├── categories.py              ← ItemType, Category enums
│       ├── risk.py                    ← RiskLevel, ReviewStatus, EvidenceStatus enums
│       └── fy.py                      ← FY helpers (FY = 1 Jul – 30 Jun)
├── frontend/                          ← Next.js (App Router)
│   ├── app/
│   ├── components/
│   │   └── DisclaimerBanner.tsx       ← always visible, never conditional
│   └── lib/
│       └── api.ts                     ← ALL fetch() calls here only
├── skills/                            ← domain skill packs (use skills/ not skill/)
│   ├── tax-return-specialist/
│   ├── tax-document-ingestion/
│   ├── tax-app-builder/
│   └── tax-compliance-review/
├── docs/decisions/                    ← ADRs
├── scripts/
│   ├── seed_demo.py
│   └── export_demo.py
└── tests/
```

---

## Active Edition

Set `EDITION` in `.env`. Default for development: `personal`.

| Value | DB | Storage | Auth | Target |
|---|---|---|---|---|
| `personal` | SQLite | local | none | Free public download |
| `pro` | SQLite | local | none | Paid local upgrade |
| `team` | PostgreSQL | S3 | JWT | Tax agents / firms |

Never hardcode edition checks inline. Always use `settings.*_enabled` properties
from `app/config.py`. See `skills/tax-app-builder/references/recommended-architecture.md`.

---

## How to Run

```bash
make up              # start personal/pro (SQLite)
make up-team         # start team (PostgreSQL)
make down            # stop
make migrate         # run Alembic migrations
make verify          # lint + tests + schema validation (must pass before commit)
make test            # backend + frontend tests only
make seed-demo       # insert synthetic demo data (5 items, all risk levels)
make export-demo     # generate demo export package
make validate-schema # validate all skill schemas against examples
make new-migration name="describe_change"
```

`make verify` must pass before any commit. If it doesn't exist yet, create it.

---

## Three Adapter Rules — Non-Negotiable

Enforced on every PR. See `docs/decisions/001-adapter-pattern.md`.

### 1. AI — adapter only

```python
# CORRECT
from app.ai.factory import get_provider
result = await get_provider().classify(text, doc_id, fy, skill_context)

# WRONG — never in business logic
import anthropic
client = anthropic.Anthropic()
```

### 2. Database — repository only

```python
# CORRECT
from app.repositories.tax_item_repo import TaxItemRepository
items = await TaxItemRepository(db).find_by_session(session_id)

# WRONG — never in services or routers
await db.execute(text("SELECT * FROM tax_items WHERE ..."))
```

### 3. Storage — adapter only

```python
# CORRECT
from app.storage.factory import get_storage_backend
path = await get_storage_backend().save(key, data, content_type)

# WRONG — never in services or routers
with open(f"./uploads/{filename}", "wb") as f: ...
```

---

## Canonical Table Names

Exact names for all models, repositories, migrations, API docs, and tests.
Do not use retired names: `extracted_items`, `ai_runs`.

| Table | Purpose |
|---|---|
| `tax_sessions` | Groups documents for one user + one financial year |
| `documents` | Uploaded file, `file_hash` (SHA-256), storage path |
| `document_pages` | Per-page OCR text and confidence |
| `tax_items` | Classified line items — the canonical product row |
| `classification_results` | Raw validated AI JSON per classification run |
| `review_actions` | User confirm / correct events (append-only) |
| `audit_events` | Full event log — **append-only, never UPDATE/DELETE** |
| `export_packages` | Generated review package metadata |
| `jobs` | Long-running job tracking (ingestion, OCR, classification, export) |
| `app_settings` | Runtime key/value config |
| `users` | Team edition only |
| `workspaces` | Team edition only |
| `workspace_members` | Team edition only |

---

## Canonical Status Values

### Tax session status
`draft` · `importing` · `reviewing` · `ready_for_export` · `exported` · `archived`

### Document status
`uploaded` · `stored` · `text_extracted` · `ocr_required` · `ocr_completed`
`extraction_failed` · `normalised` · `duplicate_detected` · `ready_for_classification`
`classified` · `classification_failed` · `needs_review` · `reviewed` · `exported`

### Review status (used by tax_items AND compliance_review — must be consistent)
`auto_classified` · `needs_user_review` · `needs_tax_agent_review`
`user_confirmed` · `excluded_by_user` · `ready_for_export`

### Evidence status
`complete` · `partial` · `missing_or_incomplete` · `not_required`

### Risk level
`low` · `medium` · `high`

### Job status
`queued` · `running` · `succeeded` · `failed` · `cancelled` · `retrying`

---

## Financial Year Rules

- Australian FY = **1 July – 30 June**
- All FY logic in `app/constants/fy.py` — never inline date arithmetic elsewhere
- Every `TaxSession`, `Document`, and `TaxItem` carries `financial_year` (e.g. `"2025-2026"`)
- Every AI output must include `financial_year` and `date_in_financial_year`
- Date outside declared FY → `risk_level: high`, `review_status: needs_user_review`
- `FINANCIAL_YEAR` env var sets the default for new sessions

---

## Deduplication Rules

Run both checks on every upload — both are required:

1. **Hash check** — SHA-256 of raw file bytes vs `documents.file_hash` in same session
2. **Content check** — supplier + amount + date vs `tax_items` in same session (skip if any null)

On match: `category: duplicate_document`, `risk_level: high`, preserve both records — never auto-delete.

---

## Schema Versions

| Schema | Current version | Location |
|---|---|---|
| `tax_analysis_output` | `1.1` | `skills/tax-return-specialist/schemas/` |
| `document_ingestion` | `1.1` | `skills/tax-document-ingestion/schemas/` |
| `compliance_review` | `1.1` | `skills/tax-compliance-review/schemas/` |
| `app_config` | `1.1` | `skills/tax-app-builder/schemas/` |

If changing schema fields: bump version, update example, update validator, add migration if persisted.

---

## Files Requiring Extra Care

| File / Directory | Rule |
|---|---|
| `alembic/versions/` | Never edit existing migrations. Always add new ones. |
| `skills/*/schemas/*.json` | Bump version on breaking changes. Update examples + validators. |
| `app/constants/` | Changes affect classification, UI, and exports. Update tests. |
| `audit_events` table | Append-only. Never UPDATE or DELETE rows. |
| `review_actions` table | Append-only. |
| `correction_history` in AI JSON | Append-only array. Never overwrite entries. |
| `DisclaimerBanner.tsx` | Must be visible on every page. Never conditional. |
| `docs/decisions/` | Never rewrite existing ADRs. Add a new ADR for changed decisions. |

---

## Before Every Commit

- [ ] `make verify` passes
- [ ] No vendor SDK imported outside `app/ai/providers/` or `app/ocr/providers/`
- [ ] No raw SQL outside `app/repositories/`
- [ ] No `open()` / `pathlib.write` / `boto3` outside `app/storage/`
- [ ] No tax logic hardcoded in routers, services, or UI
- [ ] `DisclaimerBanner` present on every page
- [ ] New migrations are new files — no edits to existing ones
- [ ] `audit_events` and `review_actions` rows only ever inserted
- [ ] No UI wording violates product boundary (see Preferred Vocabulary below)

---

## Preferred Vocabulary

**Use:** candidate deduction · likely category · tax-ready summary · requires review
· supporting evidence · evidence package · inferred from uploaded data · pre-agent handoff

**Never use:** deductible · ATO-approved · guaranteed · final · lodge now
· refund maximiser · AI tax agent · automatic ATO submission · refund amount

When in doubt: `skills/tax-return-specialist/SKILL.md` section 7.

---

## Compliance Disclaimer (required on every page)

> This tool helps organise tax information and prepare a review package.
> It does not provide final tax advice, does not lodge tax returns, and does not
> replace review by the user or a registered tax agent.

---

## Skill Reading Order for Common Tasks

| Task | Read first |
|---|---|
| Tax classification logic | `skills/tax-return-specialist/SKILL.md` |
| Document upload / OCR | `skills/tax-document-ingestion/SKILL.md` |
| Review queue / export readiness | `skills/tax-compliance-review/SKILL.md` |
| App scaffold / models / API | `skills/tax-app-builder/SKILL.md` |
| Any of the above | This file (`CLAUDE.md`) first, always |
