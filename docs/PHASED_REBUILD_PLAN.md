# Phased Rebuild Plan — tax-return-ai

> Generated: 2026-05-14
> Design approach: Incremental, Docker-compatible, Raspberry Pi viable

---

## Overview

10 phases, ordered by dependency. Each phase is designed to be independently deployable without breaking the previous phase.

```
Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 → Phase 7 → Phase 8 → Phase 9
Freeze    Define    Auth      Doc       OCR       Review    Encrypted  Local AI  Prod      Desktop
+Audit    Workflow  +Encrypt  Lifecycle Redesign  UX        Export     Layer     Hardening Readiness
```

**Legend**: 🔴 Blocking dependency | 🟡 Non-blocking | ✅ Can run standalone

---

## Phase 0 — Freeze + Architecture Audit

**Duration**: 1-2 days  
**Risk**: Low  
**Status**: ✅ COMPLETE (see AUDIT_AND_REDESIGN_PLAN.md)

### Done
- [x] Full codebase read (all files audited)
- [x] Architecture assessment (adapter patterns, middleware, routers)
- [x] Security review (auth, encryption, data leaks)
- [x] UX review (workflow, guidance, information architecture)
- [x] Data model review (schema, missing fields, relationships)
- [x] Provider audit (AI, OCR, storage)
- [x] Infrastructure audit (Docker, deployment, CI)
- [x] Produced AUDIT_AND_REDESIGN_PLAN.md

### Immediate Fixes Applied During Audit
- [x] Negative retry_seconds bug in rate limiter (`rate_limit.py`)
- [x] Document actions (delete, retry) added to session page
- [x] Document API methods added (`deleteDocument`, `updateDocument`)
- [x] Session delete + archive + rename added to frontend
- [x] Health check indicator on home page
- [x] Comprehensive README written

---

## Phase 1 — Product Definition + Workflow Redesign

**Duration**: 2-3 days  
**Risk**: Medium  
**Dependencies**: None (runs on top of existing code)

### User Workflow (target)

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ 1. Unlock │──▶│ 2. Select │──▶│ 3. Upload │──▶│ 4. Review │──▶│ 5. Export │
│ Workspace │    │ Tax Year  │    │ Docs      │    │ Items     │    │ Pack      │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
                                                        │
                                                        ▼
                                                 ┌──────────┐
                                                 │ 6. Send   │
                                                 │ to Agent  │
                                                 └──────────┘
```

### Deliverables

#### Frontend
- [ ] Stepped/wizard UI replacing flat tabs
- [ ] Step 1: "Select Tax Year" — year picker, session selector or create new
- [ ] Step 2: "Upload Documents" — drag-drop area, progress per file, batch status
- [ ] Step 3: "Review Items" — improved review panel with approve/flag/exclude/reject per item
- [ ] Step 4: "Export" — review pack generation, encrypted password prompt, download
- [ ] Progress indicator (Step 1 of 4) with visual state feedback
- [ ] Privacy indicator badge ("🔒 Data stored locally" / "☁️ AI via cloud")
- [ ] Empty states with guidance messages
- [ ] Calm, minimalist design — reduce visual noise, remove admin-feeling debug elements

#### Backend
- [ ] No backend changes — this is purely UX restructure

### Files to Create
- `frontend/app/workspace/page.tsx` — stepped workflow page
- `frontend/components/WorkflowStepper.tsx` — step indicator component
- `frontend/components/StepUpload.tsx` — upload step (replaces inline upload)
- `frontend/components/StepReview.tsx` — review step (consolidates items + review tabs)
- `frontend/components/StepExport.tsx` — export with encryption options

### Files to Modify
- `frontend/app/page.tsx` — redirect to workspace or step 0
- `frontend/app/session/[id]/page.tsx` — keep as legacy detail view, redirect from new flow
- `frontend/components/DocumentUploader.tsx` — refactor for step UX

---

## Phase 2 — Authentication + Encryption

**Duration**: 3-5 days  
**Risk**: High  
**Dependencies**: Phase 1 UX (new pages host auth UI) 🔴

### Authentication

- [ ] Master password unlock (personal/pro edition)
- [ ] Derive encryption key from password (Argon2id → AES-256-GCM)
- [ ] Server-side session with timeout + auto-lock
- [ ] Recovery key generation (paper backup)
- [ ] JWT auth for team edition (deferred to future phase)

### Encryption at Rest

- [ ] Column-level encryption for:
  - `TaxItem.amount` → `encrypted_amount`
  - `TaxItem.description` → `encrypted_description`
  - `DocumentPage.text` → `encrypted_text`
  - `ClassificationResult.raw_input` → `encrypted_raw_input`
  - `ClassificationResult.raw_output` → `encrypted_raw_output`
  - `ClassificationResult.parsed_output` → `encrypted_parsed_output`
  - `ExportPackage.export_data` → `encrypted_export_data`
- [ ] Key derivation: master password → Argon2id → AES-256 key
- [ ] Key stored in memory only (never persisted)
- [ ] Auto-lock on session timeout → wipe in-memory key
- [ ] SQLite encryption via `sqlcipher` or application-layer encryption

### Files to Create
- `app/crypto/__init__.py` — encryption module (AES-256-GCM, Argon2id)
- `app/crypto/key_derivation.py` — key derivation from master password
- `app/crypto/field_encryption.py` — encrypt/decrypt decorators or descriptor
- `app/auth/__init__.py` — auth service
- `app/auth/master_password.py` — master password verification
- `app/models/encryption_key.py` — key metadata model
- `frontend/components/UnlockScreen.tsx` — master password entry
- `frontend/components/FirstTimeSetup.tsx` — initial password + recovery key

### Files to Modify
- `app/main.py` — add auth middleware
- `app/config.py` — add encryption config
- `app/models/*.py` — add encrypted columns
- `frontend/app/layout.tsx` — wrap in auth check

---

## Phase 3 — Document Lifecycle Redesign

**Duration**: 2-3 days  
**Risk**: Medium  
**Dependencies**: Phase 2 (encryption for new models) 🔴

### New Document States

```
uploaded
  → extracting_text
  → text_extracted
  → classifying
  → classified
  → needs_review
  → reviewed
  → included_in_report
  → archived
```

### Changes
- [ ] Simplify status enum: 9 states (down from 14+)
- [ ] Add user-facing document status display in workflow
- [ ] Add "Retry extraction" action for failed documents
- [ ] Add "Exclude from report" action
- [ ] Add document-level notes/comments
- [ ] Soft-delete for documents (recoverable)
- [ ] Retention policy config: auto-archive after N days

### Files to Modify
- `app/models/document.py` — status enum, soft_delete, retention, notes
- `app/services/ingestion/pipeline.py` — new status transitions
- `app/constants/risk.py` — align status constants
- `app/routers/documents.py` — soft-delete, restore endpoint
- `frontend/components/StepUpload.tsx` — richer document status display
- `docs/decisions/` — new ADR for lifecycle

---

## Phase 4 — OCR Pipeline Redesign

**Duration**: 2-3 days  
**Risk**: Medium  
**Dependencies**: Phase 3 (document lifecycle states) 🟡

### Layered OCR Strategy

```
Layer 1: Direct PDF text extraction (pdfplumber, PyMuPDF)
  → If text found and confidence > 0.8: done

Layer 2: Local OCR fallback (Tesseract with image preprocessing)
  → If PDF has no extractable text OR image files
  → Includes: grayscale, binarization, deskew, contrast adjustment

Layer 3: Advanced OCR (optional, future)
  → PaddleOCR / Surya for difficult documents
  → Container-level opt-in only
```

### Changes
- [ ] Add PyMuPDF as direct text extraction (faster than pdfplumber for text-only PDFs)
- [ ] Add Pillow-based image preprocessing before Tesseract
- [ ] Add confidence threshold gating (Layer 1 → fallback if confidence < 0.8)
- [ ] Add asyncio timeout to OCR pipeline (enforce `processing_timeout_seconds`)
- [ ] Add OCR strategy metadata to document (which layer succeeded)
- [ ] Refactor single-page/multi-page Tesseract code duplication

### Files to Modify
- `app/ocr/providers/tesseract.py` — preprocessing + deduplicated code
- `app/ocr/providers/pdfplumber.py` — optional PyMuPDF add
- `app/ocr/dispatch.py` — layered dispatch with confidence gating
- `app/services/ingestion/pipeline.py` — timeout enforcement
- `requirements.txt` — add Pillow, optional PyMuPDF

---

## Phase 5 — Review Workflow Redesign

**Duration**: 2-3 days  
**Risk**: Low  
**Dependencies**: Phase 1 (new UX), Phase 3 (document lifecycle)

### New Review States (for TaxItem)

```
draft
  → needs_user_review
  → user_confirmed
  → excluded_by_user
  → needs_tax_agent_review
```

### Changes
- [ ] Replace boolean `needs_review` with proper `review_status` enum
- [ ] Add "Confirm", "Exclude", "Flag for Agent" actions
- [ ] Add item-level notes for user or agent
- [ ] Add batch confirm/exclude (bulk operations on filtered views)
- [ ] Add review statistics: items confirmed, excluded, pending
- [ ] Add undo for last review action

### Files to Modify
- `app/models/tax_item.py` — replace `needs_review` with `review_status`
- `app/schemas/tax_item.py` — update schemas
- `app/services/classification/__init__.py` — set initial review_status
- `app/routers/items.py` — update review endpoint
- `app/constants/risk.py` — update review_status enum
- `frontend/components/StepReview.tsx` — new review actions
- `frontend/components/ItemTable.tsx` — updated status display
- `alembic/versions/` — migration for boolean→enum

---

## Phase 6 — Encrypted Export System

**Duration**: 3-4 days  
**Risk**: High  
**Dependencies**: Phase 2 (encryption primitives) 🔴

### Export Structure

```
tax-review-pack-[fy]-[session-id].enc.zip
├── review-report.pdf              ← human-readable summary
├── extracted-items.json.enc       ← encrypted item data
├── evidence-index.csv.enc         ← encrypted evidence log
├── source-documents/              ← encrypted document copies
│   ├── doc-1.pdf.enc
│   └── doc-2.pdf.enc
└── metadata.json                  ← unencrypted (session info, FY, timestamps)
    └── "encryption": "AES-256-GCM"
    └── "key_hint": "argon2id(session_password)"
```

### MVP (this phase)
- [ ] Password-protected encrypted ZIP (AES-256)
- [ ] Password prompt before export download
- [ ] Export format selector: encrypted JSON / encrypted CSV / PDF summary
- [ ] Export history with export status (not full data re-display)

### Future
- [ ] Public/private key sharing for tax agents
- [ ] Agent portal with decryption capability

### Files to Create
- `app/crypto/export_encryption.py` — ZIP encryption, manifest generation
- `app/services/export/encrypted_builder.py` — encrypted export package builder
- `scripts/generate_pdf_report.py` — report.pdf generation from export data
- `frontend/components/EncryptedExportPrompt.tsx` — password input for export

### Files to Modify
- `app/routers/export.py` — add encrypted export endpoint
- `app/services/export/__init__.py` — preserve plaintext export, add encrypted variant
- `frontend/components/StepExport.tsx` — encryption options UI
- `requirements.txt` — add pyzipper (AES-256 ZIP) or cryptography

---

## Phase 7 — Optional Local AI Layer

**Duration**: 3-5 days  
**Risk**: Medium  
**Dependencies**: Phase 2 (encryption), Phase 5 (review states) 🟡

### Strategy

```
Preferred order for classification:
1. Deterministic rules (keyword matching, regex patterns)
2. Schema validation (is the data well-formed?)
3. Local AI (Ollama / llama.cpp on device)
4. Cloud AI (Anthropic/OpenAI — only with explicit user consent + data sovereignty notice)
```

### Deliverables
- [ ] Create `OllamaProvider` (via Ollama API on localhost)
- [ ] Create `LlamaCppProvider` (via llama.cpp server)
- [ ] Add local-AI detection and provider fallback chain
- [ ] Add data jurisdiction notice when using cloud AI
- [ ] Add explicit consent checkbox for cloud AI (opt-in, never default)
- [ ] Change default `ai_provider` to `mock` (not `anthropic`)

### Files to Create
- `app/ai/providers/ollama.py` — local AI via Ollama
- `app/ai/providers/llamacpp.py` — local AI via llama.cpp
- `app/ai/deterministic.py` — rule-based classification engine

### Files to Modify
- `app/config.py` — change default `ai_provider` to `mock`
- `app/ai/factory.py` — add Ollama/llama.cpp support
- `app/services/classification/__init__.py` — add provider fallback chain
- `frontend/components/StepUpload.tsx` — add data sovereignty indicator
- `frontend/components/PrivacyNotice.tsx` — cloud AI consent UI

---

## Phase 8 — Production Hardening

**Duration**: 3-5 days  
**Risk**: Low  
**Dependencies**: All previous phases complete 🔴

### Deliverables
- [ ] Router → Repository refactor (systematic: all `db.execute()` moved to repository classes)
- [ ] Add pagination to all list endpoints (`offset`/`limit` params)
- [ ] Add asyncio timeout to ingestion pipeline (`asyncio.wait_for`)
- [ ] Add persistent job queue (switch from BackgroundTasks to ARQ + Redis)
- [ ] Add rate limit persistence (SQLite-backed or Redis-backed rate limiter)
- [ ] Add document-level rate limiting (separate from session-level)
- [ ] Add UUID validation on all path parameters
- [ ] Add input validation middlewares (body size, content-type)
- [ ] Add Docker resource limits (`mem_limit`, `cpus`)
- [ ] Add Docker secrets for API keys
- [ ] Add data retention cron job (auto-purge expired data)
- [ ] Add database migration health check in deploy script
- [ ] DRY up AI provider code (shared prompt builder, JSON parser, ATO mapping)
- [ ] Add graceful shutdown handling (SIGTERM for running jobs)

### Files to Create
- `app/repositories/*.py` — full repository layer (one per model)
- `app/middleware/input_validation.py` — request validation middleware
- `app/services/job/worker.py` — ARQ worker for persistent queue
- `app/services/cleanup.py` — data retention cleanup cron

### Files to Modify
- `app/routers/*.py` — replace `db.execute` with repository calls
- `app/main.py` — add new middleware, ARQ worker startup
- `app/middleware/rate_limit.py` — SQLite-backed storage
- `docker-compose.yml` — resource limits, redis service, secrets
- `app/ai/providers/anthropic.py` + `openai.py` — extract shared code
- `app/services/ingestion/pipeline.py` — timeout enforcement
- `scripts/deploy.sh` — migration health check

---

## Phase 9 — Desktop Packaging Readiness

**Duration**: 2-3 days  
**Risk**: Low  
**Dependencies**: Phase 2 (auth), Phase 6 (encryption) 🟡

### Deliverables
- [ ] Audit all dependencies for ARM64 compatibility (Raspberry Pi)
- [ ] Add PWA support (service worker, manifest, offline page)
- [ ] Add auto-update mechanism (watchtower or similar)
- [ ] Add Tauri/Electron shell wrapper evaluation (recommendation only)
- [ ] Add Electron packaging config (optional, defer to project decision)
- [ ] Add snap/flatpak config (optional)
- [ ] Document desktop packaging strategy

### Files to Create
- `frontend/public/manifest.json` — PWA manifest
- `frontend/public/sw.js` — service worker for offline
- `electron/` — optional Electron shell (deferred decision)
- `docs/DESKTOP_STRATEGY.md` — desktop packaging analysis

### Files to Modify
- `frontend/app/layout.tsx` — PWA meta tags
- `docker-compose.yml` — optional watchtower service

---

## Dependency Graph

```
Phase 0 (Audit)
   │
   ▼
Phase 1 (Workflow Redesign) ──────────────────────────┐
   │                                                    │
   ▼                                                    │
Phase 2 (Auth + Encryption) ──────┐                     │
   │                               │                    │
   ▼                               ▼                    ▼
Phase 3 (Doc Lifecycle)    Phase 6 (Encrypted Export)  │
   │                                                    │
   ▼                                                    │
Phase 4 (OCR Pipeline)                                  │
   │                                                    │
   ▼                                                    ▼
Phase 5 (Review Workflow) ───────────── Phase 7 (Local AI)
   │                                                    │
   ▼                                                    ▼
Phase 8 (Production Hardening) ←────────────────────────┘
   │
   ▼
Phase 9 (Desktop Readiness)
```

---

## Estimated Total Effort

| Phase | Days | Risk | Critical Path |
|---|---|---|---|
| 0 — Freeze + Audit | 1-2 | Low | ✅ Done |
| 1 — Workflow Redesign | 2-3 | Medium | Starts here |
| 2 — Auth + Encryption | 3-5 | High | 🔴 Blocks 3, 6 |
| 3 — Doc Lifecycle | 2-3 | Medium | Blocked by 2 |
| 4 — OCR Pipeline | 2-3 | Medium | Can start with 3 |
| 5 — Review Workflow | 2-3 | Low | Blocked by 1, 3 |
| 6 — Encrypted Export | 3-4 | High | Blocked by 2 |
| 7 — Local AI | 3-5 | Medium | After 2, 5 |
| 8 — Prod Hardening | 3-5 | Low | After all |
| 9 — Desktop Readiness | 2-3 | Low | After 2, 6 |

**Total: 23-36 days** (2-3 months for a single developer)

---

## Quick Wins (Can Do Immediately)

These are independent of the phased plan and can be done now:

1. **Change default AI provider to `mock`** — `app/config.py` line `ai_provider: str = "mock"` (currently `"anthropic"`)
2. **Add Ollama provider** — ~1 day, creates local AI option
3. **Router → repository migration per endpoint** — incremental, tackle one router at a time
4. **Add pagination to list endpoints** — ~4 hours, low risk
5. **Add UUID validation middleware** — ~2 hours
6. **DRY AI provider code** — ~1 day, reduces maintenance burden
7. **Add asyncio timeout to ingestion pipeline** — ~2 hours
8. **Add Tesseract image preprocessing** — ~4 hours, improves OCR quality significantly
