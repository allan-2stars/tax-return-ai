# Audit Report: Current Build (tax-return-ai)

## Executive summary
The current repository is a usable **prototype scaffold**, not a production-ready confidential tax document system. It has real end-to-end flows (session creation, upload, OCR dispatch, AI classification, review actions, export, audit logs, jobs UI) and a practical Docker-first setup for local deployment behind Cloudflare Tunnel. 

However, for a privacy-preserving Australian tax evidence-pack product, there are critical gaps: no authentication in personal edition, no encryption at rest, plaintext storage of OCR/classification/export payloads, non-persistent in-process background jobs, incomplete local-AI/offline fallback strategy, and limited hardening/testing for security and failure modes. 

**Decision**: Use as scaffolding with major redesign (**Option B**), not full rewrite.

## Keep / Replace / Rewrite
| Area | Keep | Replace | Rewrite | Notes |
|---|---|---|---|---|
| FastAPI app structure | ✅ |  |  | Router/service/model separation is workable.
| Next.js frontend baseline | ✅ |  |  | Good scaffold; workflow UX needs redesign.
| Docker-first deployment | ✅ |  |  | Compose + Dockerfiles are solid starting point.
| OCR adapter pattern | ✅ |  |  | Dispatch/provider abstraction is useful.
| AI adapter pattern | ✅ |  |  | Provider abstraction exists; behavior must change.
| Job execution model |  | ✅ |  | Replace `BackgroundTasks` with persistent queue/worker.
| Security model |  |  | ✅ | Add auth, encryption, key/session lifecycle.
| Data model for confidential app |  | ✅ |  | Extend current model for users/review states/encryption metadata.
| Export subsystem |  | ✅ |  | Stop persisting full export payload; add encrypted packages.
| Storage subsystem |  | ✅ |  | Current storage abstraction exists but is bypassed in ingestion.
| Compliance workflow UX |  | ✅ |  | Move from tabbed admin UI to guided steps.
| Test strategy |  | ✅ |  | Broaden to security/integration/e2e and failure recovery.

## Current architecture diagram (implemented)
```text
Browser (Next.js frontend)
  -> /api calls
FastAPI backend
  - Routers: sessions, documents, items, jobs, compliance, export, audit, monitoring
  - Middleware: CORS, security headers, request logging, in-memory rate limit, UUID checks
  - In-process BackgroundTasks for ingestion pipeline
  - Services: OCR dispatch, AI classification, compliance, export, audit, jobs
  - SQLAlchemy async ORM
SQLite database (default) / PostgreSQL (configurable)
Local file system volume (./data) for DB/uploads (intended)
Cloud AI providers (Anthropic/OpenAI) optional by config; mock provider available
Cloudflare Tunnel terminates HTTPS externally
```

## Current user workflow (implemented)
1. User creates/selects a tax session.
2. User uploads one or many documents (`/api/documents/upload` or `/upload/batch`).
3. Backend creates job + document rows, then background ingestion runs.
4. OCR extraction stores `document_pages` text/confidence.
5. AI classification creates `tax_items`, `document_items`, `classification_results`.
6. User reviews items (approve/flag/delete/edit amount).
7. User runs compliance review panel.
8. User exports JSON/CSV and can view export history.

## Implemented vs documented
### Actually implemented
- CRUD/session/doc/item/job/audit/compliance/export endpoints.
- OCR dispatch with pdfplumber + tesseract + identity text path.
- AI providers: mock/openai/anthropic with adapter abstraction.
- Dedup by file hash within session.
- Review state currently boolean (`needs_review`) with review action log table.
- Export generation and persistence of export history + payload.
- Frontend pages for home + session with tabbed panels.
- Backend and frontend unit/integration test suites present.

### Documented but not implemented (or only partial)
- Master-password login/lock flow.
- Encryption at rest for sensitive fields and files.
- Encrypted export package as default.
- Persistent queue/worker (ARQ/Redis-style) with crash recovery.
- Full repository-layer enforcement (routers still run direct queries).
- Canonical multi-state review lifecycle enums in DB.
- Local LLM chain as first-class option with consented cloud escalation.
- Secure deletion and retention policy execution.

## Docker/deployment audit
### What works
- `docker-compose.yml` runs frontend + backend with health checks.
- Ports bound to localhost (`127.0.0.1`), compatible with Cloudflare Tunnel.
- Backend runtime includes OCR dependencies (tesseract/poppler binaries).
- Persistent volume mount `./data:/app/data` for local data continuity.

### Gaps
- Compose currently defines only `frontend` and `backend`; no separate worker, DB service, object storage, Redis, or OCR service isolation.
- No resource limits, read-only FS, non-root user hardening, or secret mounts.
- S3 backend is stubbed (`NotImplementedError`), team/pro storage path not production-ready.
- No dedicated health check for background worker because worker is not separate.

## Security gaps
1. **No authentication gate (critical)** for personal edition paths; all API routes are callable if network path exists.
2. **No encryption at rest (critical)** for OCR text, classification input/output, tax item descriptions/amounts, exports, and audit details.
3. **Sensitive export payload stored in DB** (`export_packages.export_data`) in plaintext.
4. **Potential secret hygiene risk**: `.env.example` includes realistic API key placeholders; no runtime secret manager integration.
5. **In-memory rate limiter** resets on restart and is per-process only.
6. **No secure deletion semantics** for uploaded files or generated outputs.
7. **Cloud AI data egress guardrails are policy-only**; no UX-level mandatory consent enforcement in API flow.
8. **No CSRF/session management controls** because no login/session layer exists yet.

## Data model gaps
- No `users` or auth `sessions` tables.
- `tax_items` uses boolean `needs_review` instead of full workflow status enum.
- No explicit audit actor identity beyond free-text `changed_by`.
- No encryption metadata fields (key version, encrypted blobs, rotation support).
- `export_packages` stores payload not metadata-only.
- No retention/deletion policy fields (`soft_deleted_at`, `expires_at`, etc.).

## Document lifecycle gaps
### Upload
- Type/size checks are present.
- Uses direct DB insert + background task; storage adapter is not used in ingestion path.

### OCR/text extraction
- Works for text/pdf/image basics.
- No confidence thresholds driving deterministic fallback logic beyond simple checks.

### Classification
- Provider abstraction is good.
- No deterministic-rules-first layer; cloud/local policy is not enforced by workflow state.

### Duplicate detection
- Hash duplicate in-session implemented.
- Content-level duplicate detection exists as helper but not integrated in pipeline.

### Item review
- Functional but coarse (approve/flag boolean), limited provenance and role support.

### Report generation
- JSON/CSV generation implemented.
- Not encrypted by default and persisted in plaintext DB.

### Deletion behavior
- Hard delete endpoints exist; secure wipe/retention/audit-strength behavior not implemented.

## OCR/classification/report gaps
- OCR provider chain lacks robust preprocessing governance and confidence-based branching strategy.
- Classification records store raw inputs/outputs in plaintext.
- No local LLM provider implementation shipped (only mock/cloud providers).
- Export is not confidentiality-preserving by default.

## AI usage audit
- Providers: `mock`, `openai`, `anthropic`.
- Raw extracted text is sent to provider when cloud provider is configured.
- Local AI support: **not implemented** beyond mock deterministic testing behavior.
- Fallback: provider code usually returns a `needs_review` item on exceptions; no orchestrated multi-provider chain with explicit privacy policy enforcement.

## UI/UX gaps
- Current UI is tabbed “admin console” style; workflow does not strongly guide user through tax-ready evidence pack steps.
- Next actions are visible but not strict enough (upload -> review -> export gating is soft).
- Document review vs item review is understandable but still technical for non-expert users.
- Design language is reasonably consistent but does not yet convey a high-trust confidential-document product standard.

## Test gaps
### Present
- Backend tests for routers/services (upload, ingestion, OCR, classification, export, compliance, jobs, providers, schema validation).
- Frontend component tests exist (requires installing missing test deps in frontend package).

### Missing/weak
- Security tests: auth, encryption, secret handling, data-leak prevention.
- End-to-end lifecycle tests in Docker (frontend+backend integration).
- Crash/restart recovery tests for in-flight ingestion jobs.
- Load/performance tests for large batches/docs.
- Pen-test style checks (IDOR, path traversal, abuse scenarios).

## Recommendation
### Options
- A. Full rewrite
- B. Use as scaffolding with major redesign
- C. Continue incremental fixes

### Recommended option: **B. Use as scaffolding with major redesign**
Why:
- Core scaffold is real and useful (API/UI models, adapters, tests, deployment baseline).
- Rewriting from zero would discard significant working behavior and slow MVP.
- Incremental fixes alone are insufficient because confidentiality/security and lifecycle architecture need cross-cutting redesign.

## Phased remediation plan
### Phase 0: freeze and audit
- Freeze feature additions.
- Finalize current-state inventory and threat model.
- Define data-classification policy for all fields/files.

### Phase 1: product definition and data model
- Lock MVP scope: tax-ready review/evidence pack only (no lodgement).
- Introduce canonical review/document status enums.
- Introduce user/session/workspace model (even personal mode should authenticate).

### Phase 2: login and encryption
- Implement master-password unlock flow.
- Add app-layer encryption (AES-256-GCM) for sensitive DB columns.
- Add key derivation/rotation design and inactivity lock.

### Phase 3: document lifecycle
- Refactor ingestion to use storage abstraction consistently.
- Add explicit lifecycle state machine transitions and validation.
- Add secure/retained deletion policy implementation.

### Phase 4: OCR pipeline
- Strengthen OCR chain: confidence gating, retries, preprocessing policy.
- Add deterministic handling for unreadable pages and user remediation prompts.

### Phase 5: review workflow
- Replace tabbed UI with guided steps and hard workflow checkpoints.
- Add clearer provenance: source snippet/page, confidence, review rationale.

### Phase 6: encrypted export
- Default to password-encrypted evidence pack export.
- Persist metadata only; do not store raw export payload.
- Include export integrity/audit metadata.

### Phase 7: local AI optional layer
- Implement local model provider (Ollama/llama.cpp style) as first-class.
- Make cloud AI opt-in with explicit consent and visible status.
- Add deterministic rules-first fallback before any LLM call.

### Phase 8: production hardening
- Introduce persistent queue worker and recovery.
- Harden containers (non-root, limits, secrets, health, observability).
- Expand test matrix: security, e2e, resilience, regression.

## Assumptions
- Live URLs (`https://tax.signpega.com`, `https://tax-api.signpega.com`) were not runtime-validated in this audit; conclusions are based on repository code/config only.
- No source code changes were made except creating this audit document.
- Existing `.env` runtime values were not printed or exposed.
