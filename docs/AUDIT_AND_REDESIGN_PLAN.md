# Audit & Redesign Plan — tax-return-ai

> Generated: 2026-05-14
> Auditor: Hermes Agent (senior software architect, security reviewer, UX reviewer)

---

## Executive Summary

After a deep audit of the entire codebase (backend, frontend, infrastructure, providers, data model, and UX), the project is assessed as **Option B: Use as scaffolding with fundamental redesign.**

The current build has a strong foundation:
- Clean adapter patterns (AI, OCR, storage, database)
- Edition-based feature gating
- Local-first defaults (SQLite, local storage, mock providers)
- Audit trail on every mutation
- Background job orchestration

However, it has critical gaps that prevent it from being a trustworthy, secure, local-first tax evidence review tool:

| Category | Verdict |
|---|---|
| **Security** | ❌ No authentication, no encryption, hard deletes, data exposed via API |
| **Data Privacy** | ❌ PII in plaintext DB, raw AI inputs persisted, export data stored indefinitely |
| **Local-First** | ⚠️ OCR is local-first ✅ but AI defaults to Anthropic (sends data to US servers) |
| **UX** | ❌ No guided workflow, feels like admin panel, no progress states, confusing review flow |
| **Schema** | ⚠️ Good hierarchy but missing encryption, user isolation, lifecycle fields |
| **Architecture** | ✅ Strong adapter pattern but routers bypass repository layer (systemic violation) |
| **Maintainability** | ⚠️ Good structure but AI providers have 80% code duplication |

---

## 1. Should This Project Be Rewritten?

**Assessment: Option B — Use as scaffolding with redesign.**

### Keep (production-worthy as-is)
- **Adapter pattern**: AI, OCR, storage, database all behind interfaces — this is the right architecture
- **Edition-based config**: `personal`/`pro`/`team` with property-gated features is clean and testable
- **Background job orchestration**: `Job` model + `run_job_sync` wrapper + progress tracking is a solid foundation
- **Audit logging**: Every mutation writes an audit event — this is crucial and works well
- **OCR pipeline**: pdfplumber + tesseract with local-fallback is the correct strategy
- **Docker Compose setup**: Localhost-only binding, health checks, restart policies — production-ready foundation
- **Error handling pattern**: Non-raising fallback on AI failure (returns needs_review result) is correct

### Redesign (incrementally — not rewrite)
- **Authentication layer** (currently absent)
- **Encryption at rest and in transit** (currently absent)
- **Guided UX workflow** (currently admin-panel)
- **Document lifecycle states** (currently too many, no user-facing progression)
- **Item review states** (currently boolean `needs_review`, needs full state machine)
- **Export encryption** (currently plaintext JSON)
- **Router↔repository architecture** (currently violated)
- **AI provider code deduplication** (80% shared code)
- **Rate limiter bug** (negative retry_seconds) — already found and fixed
- **FY date validation** (currently a stub)

### Discard / Replace
- **No code deletion needed yet** — but the following are weak and should be refactored within phases:
  - `app/routers/*.py` direct DB access (should use repositories)
  - `app/ai/providers/anthropic.py` + `openai.py` duplication → shared utility layer
  - Frontend page structure (currently single-session page with too many tabs)
  - Rate limiter (custom in-memory works but has bugs — the retry_seconds fix is already applied)

---

## 2. Component Assessment

| Component | Production Worthy? | Assessment |
|---|---|---|
| **Adapter interfaces** (AI, OCR, storage, DB base) | ✅ Yes | Clean ABCs, clear contracts |
| **Mock providers** (AI, OCR) | ✅ Yes | Deterministic, no deps, good for dev |
| **pdfplumber OCR** | ✅ Yes | Local, robust, no external calls |
| **Tesseract OCR** | ⚠️ Needs work | No image preprocessing, code duplication between single/multi-page |
| **Anthropic provider** | ❌ Needs redesign | Sends data to US, single-item only, duplicates OpenAI code |
| **OpenAI provider** | ❌ Needs redesign | Same issues as Anthropic, plus training data risk |
| **Ingestion pipeline** | ⚠️ Needs work | No streaming, no timeout, no retry on OCR failure |
| **Classification service** | ⚠️ Needs work | Stores raw inputs in DB, no multi-item support from providers |
| **Export service** | ⚠️ Needs work | No encryption, stores export data in plaintext indefinitely |
| **Compliance review** | ✅ Yes | Fully deterministic, well-structured rules |
| **Job service** | ✅ Yes | Clean lifecycle, good error capturing |
| **Rate limiter** | ⚠️ Bug fixed | In-memory works but custom (no Redis), negative retry bug now fixed |
| **Security headers** | ⚠️ Needs review | Exists but needs audit |
| **Notion of auth** | ❌ Absent | No auth of any kind implemented |
| **Encryption** | ❌ Absent | None at rest, none in transit beyond HTTPS |
| **Frontend UX** | ❌ Needs redesign | No workflow guidance, too many tabs, admin feel |
| **Docker Compose** | ✅ Yes | Good defaults, secure binding, health checks |
| **Backend Dockerfile** | ✅ Yes | Multi-stage, production-ready |
| **Frontend Dockerfile** | ✅ Yes | Multi-stage with standalone output |
| **Data model** | ⚠️ Needs extension | Missing: encryption, user, lifecycle, retention fields |

---

## 3. Dangerous or Weak Components

| Component | Risk Level | Issue |
|---|---|---|
| **No authentication** | 🔴 **Critical** | Anyone with network access can read/write all tax data |
| **PII in plaintext DB** | 🔴 **Critical** | Tax items, OCR text, export data, AI raw_input all in plaintext |
| **AI sends data externally by default** | 🔴 **Critical** | Config defaults to `ai_provider=anthropic`, sending document text to US servers |
| **Hard deletes (no recovery)** | 🟠 **High** | `DELETE FROM tax_sessions` cascades nothing — orphaned audit logs, data unrecoverable |
| **Export data persisted indefinitely** | 🟠 **High** | `export_data` TEXT column stores full tax packages with no retention |
| **Routers bypass repository layer** | 🟠 **High** | Architecture violation — `db.execute(select(...))` in routers makes future migrations harder |
| **No rate limiting on batch upload** | 🟠 **High** | 20-file batch can bypass per-file rate limits |
| **No pagination on list endpoints** | 🟡 **Medium** | Unbounded queries → memory exhaustion on large datasets |
| **Raw AI response in DB metadata** | 🟡 **Medium** | `raw_response_preview[:500]` stored in classification_results |
| **Empty OCR → skipped classification** | 🟡 **Medium** | No retry, no re-processing trigger |
| **FY date validation is a TODO stub** | 🟡 **Medium** | `date_in_financial_year = True` hardcoded |
| **Error messages leak internals** | 🟡 **Medium** | Tracebacks stored in jobs.error_message, `_error:` prefixes in OCR method names |

---

## 4. Local-First Principle Violations

| Violation | Severity | Details |
|---|---|---|
| **Cloud AI default** | 🔴 **Critical** | `ai_provider=anthropic` default sends document text to US servers. For a tool handling TFNs, salaries, and bank statements, this violates local-first and data sovereignty |
| **No offline mode** | 🟠 **High** | No offline-capability detection or graceful degradation |
| **No local AI option** | 🟠 **High** | No Ollama/llama.cpp provider — local AI is not supported at all |
| **Telemetry flag exists but unused** | 🟡 **Medium** | `telemetry_enabled=False` in config but no code path enforces it |
| **No data sovereignty selection** | 🟡 **Medium** | No option to restrict AI provider to local-only; no jurisdiction selector |

---

## 5. Confidential Data Leak Risks

| Vector | Data Leaked | Severity |
|---|---|---|
| **Anthropic/OpenAI API calls** | Full document text (PDF text, bank statements, payslips) → US servers | 🔴 **Critical** |
| **`classification_results.raw_input`** | Full OCR-extracted text stored in DB | 🟠 **High** |
| **`export_packages.export_data`** | Full tax package (all amounts, descriptions, categories) | 🟠 **High** |
| **`/api/export/{id}` response** | All income/deduction items served over network | 🟠 **High** |
| **`/api/audit`** | All audit events with details, entity IDs, timestamps | 🟡 **Medium** |
| **`/api/documents/{id}/pages`** | OCR text containing PII | 🟡 **Medium** |
| **`jobs.error_message`** | Tracebacks may expose internal paths, API key fragments | 🟡 **Medium** |

---

## 6. Architecture Support Assessment

| Capability | Currently Supported? | What's Needed |
|---|---|---|
| **Encryption** | ❌ No | Column-level encryption for PII fields, encrypted export packs, at-rest encryption config |
| **Multi-user** | ❌ No | `users`, `workspaces`, `workspace_members` tables don't exist; no auth middleware |
| **Recovery keys** | ❌ No | No key management system at all |
| **Secure exports** | ❌ No | Exports are plaintext JSON via HTTP |
| **Desktop packaging** | ⚠️ Partial | Docker-based already, but no Electron/Tauri shell, no auto-update |
| **Local AI** | ❌ No | No Ollama/llama.cpp provider; only cloud AI or mock |
| **Background workers** | ✅ Yes | FastAPI BackgroundTasks-based (single-process); no Celery/RQ/ARQ |
| **Document lifecycle tracking** | ⚠️ Partial | Document status exists but states are undocumented, no user-facing lifecycle UI |
| **Offline mode** | ❌ No | No PWA, no service worker, no cache layer |
| **Queue-based processing** | ⚠️ Partial | BackgroundTasks works but has no persistence — jobs are lost on restart |
| **Resumable jobs** | ❌ No | Job state exists but no resume mechanism on subsequent runs |
| **Data retention policies** | ❌ No | No scheduled cleanup, no expiry, no archive workflow |

---

## 7. Data Model Sufficiency

The current data model is **good for MVP but insufficient for production**.

### Strengths
- Clean hierarchy: `TaxSession → Document/Item → DocumentPage/DocumentItem`
- UUID primary keys consistently
- Audit trail on every mutation
- Timestamps everywhere

### Gaps

**Missing tables:**
- `users` — user accounts
- `workspaces` / `workspace_members` — multi-user isolation
- `encryption_keys` — key management for at-rest encryption
- `sessions` — server-side auth sessions
- `processing_queue` — persistent job queue (currently using ephemeral BackgroundTasks)

**Missing fields:**
- `encrypted_*` columns on TaxItem (amount, description), DocumentPage (text), ClassificationResult (raw_input, raw_output)
- `user_id` on TaxSession
- `soft_deleted_at` on all models (for recoverable deletions)
- `retention_days`, `expires_at`, `purged_at` for lifecycle management
- `review_status` enum column on TaxItem (currently only boolean `needs_review`)
- `classification_strategy` on ClassificationResult (deterministic vs AI vs local AI)

---

## 8. UX Assessment

The current UX is functional but **feels like an internal admin panel, not a consumer product.**

### Current Problems
- **No guided workflow** — user lands on home page with sessions, but no "what do I do next" indicator
- **Too many tabs** — Items / Needs Review / Export / Jobs / Compliance — confusing overlap
- **Document lifecycle is hidden** — documents are in a collapsed `<details>` at the bottom
- **No progress indicator** — no "step 1 of 4" navigation
- **"Approve" vs "Delete" confusion** — user asked specifically about this
- **No empty state guidance** — empty sessions show nothing useful
- **No review confirmation** — marking an item approved gives no feedback
- **Rate limiting returns confusing negative seconds** (now fixed)
- **No workspace concept** — no branding, no privacy indicator, no security feeling
- **No tax-year organization** beyond a dropdown on create

### UX Should Feel Like
> Calm, trustworthy, minimalist, document-focused, privacy-oriented, guided workflow

---

## 9. Biggest Technical Debts

| Debt | Impact | Effort to Fix |
|---|---|---|
| **No auth layer** | All data public | **High** — new middleware, models, schemas, frontend pages |
| **No encryption** | All PII in plaintext | **High** — column encryption, export encryption, key management |
| **Router bypasses repository** | Architecture erosion | **Medium** — refactor 9 routers to use 12+ repositories |
| **AI provider code duplication** | Hard to maintain | **Low** — extract shared code into utils |
| **Rate limiter not persisted** | State lost on restart | **Medium** — could add Redis or SQLite-backed storage |
| **No pagination** | OOM on large datasets | **Low** — add offset/limit to all list endpoints |
| **BackgroundTasks not persistent** | Jobs lost on crash | **High** — switch to ARQ/RQ/Celery with message broker |
| **Single-item AI response** | Multi-doc bank statements get one result | **Low** — update providers to handle list responses |
| **No image preprocessing for Tesseract** | Poor OCR quality on raw scans | **Low** — add Pillow preprocessing pipeline |

---

## Summary: What to Do

**Approach: Option B — Scaffolding with Redesign**

Keep the adapter architecture, Docker setup, edition gating, audit system, OCR pipeline, and job framework. 

Redesign:
1. Add auth + encryption (Phase 2)
2. Rewrite UX with guided workflow (Phase 1 + 3)
3. Refactor routers → repositories (Phase 0)
4. Add local AI option (Phase 7)
5. Switch to persistent queue (Phase 8)

See `PHASED_REBUILD_PLAN.md` for the detailed implementation roadmap.
