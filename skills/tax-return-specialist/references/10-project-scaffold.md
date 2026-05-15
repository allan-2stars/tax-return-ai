# Project Scaffold

See `skills/tax-app-builder/SKILL.md` section 7 for the full annotated folder tree.

## Canonical Folder Roots

| Root | Purpose |
|---|---|
| `app/` | FastAPI backend |
| `app/ai/providers/` | AI provider adapters (base + anthropic + openai + mock) |
| `app/storage/` | Storage adapters (base + local + s3 + factory) |
| `app/ocr/providers/` | OCR adapters (base + pdfplumber + tesseract + mock) |
| `app/models/` | SQLAlchemy ORM models — use canonical table names |
| `app/repositories/` | All DB queries — nowhere else |
| `app/services/` | Business logic — calls repositories and adapters only |
| `app/constants/` | Tax categories, risk enums, FY helpers |
| `frontend/` | Next.js App Router |
| `frontend/lib/api.ts` | All fetch() calls — nowhere else |
| `skills/` | Domain skill packs |
| `alembic/versions/` | Migrations — append only, never edit existing |
| `tests/` | Backend + frontend tests |
| `scripts/` | seed_demo.py, export_demo.py |

## Canonical Table Names

`tax_sessions` · `documents` · `document_pages` · `tax_items`
`classification_results` · `review_actions` · `audit_events`
`export_packages` · `jobs` · `app_settings`
`users` (team) · `workspaces` (team) · `workspace_members` (team)

Retired names — do not use: `extracted_items` · `ai_runs`

## Financial Year Helper

```python
# app/constants/fy.py
from datetime import date, datetime

FY_BOUNDARIES = {
    "2023-2024": (date(2023, 7, 1), date(2024, 6, 30)),
    "2024-2025": (date(2024, 7, 1), date(2025, 6, 30)),
    "2025-2026": (date(2025, 7, 1), date(2026, 6, 30)),
    "2026-2027": (date(2026, 7, 1), date(2027, 6, 30)),
}

def is_in_financial_year(d, fy: str):
    if d is None: return None
    if isinstance(d, str): d = datetime.strptime(d, "%Y-%m-%d").date()
    start, end = FY_BOUNDARIES[fy]
    return start <= d <= end

def fy_label(fy: str) -> str:
    start, end = FY_BOUNDARIES[fy]
    return f"{start.strftime('%-d %B %Y')} – {end.strftime('%-d %B %Y')}"

def current_fy() -> str:
    today = date.today()
    year = today.year if today.month >= 7 else today.year - 1
    return f"{year}-{year + 1}"
```

## Key Test Cases (all must pass in `make verify`)

| File | Covers |
|---|---|
| test_schema_validation.py | All 4 schemas, valid + invalid examples |
| test_classifier.py | salary_wages, tools_equipment, work_from_home, out_of_scope |
| test_deduplication.py | hash match, supplier+amount+date match, null skips |
| test_fy_validator.py | in-FY, before-FY, after-FY, None, unknown FY |
| test_out_of_scope.py | BAS, rental, crypto, SMSF |
| test_review_queue.py | high-risk first, confirmed excluded, out-of-scope flagged |
| test_provider_swap.py | mock provider → same interface as real |
| test_storage_swap.py | local → mock → same interface |
