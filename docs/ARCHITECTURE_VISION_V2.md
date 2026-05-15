# Architecture Vision v2 — tax-return-ai

> Target state after all rebuild phases

---

## Core Architecture Principle

```
                 ┌──────────────────┐
                 │   USER LAYER     │
                 │  (Frontend/PWA)  │
                 └────────┬─────────┘
                          │ HTTPS
                 ┌────────▼─────────┐
                 │  AUTH GATE       │
                 │  (Master Password │
                 │   + Session)     │
                 └────────┬─────────┘
                          │
                 ┌────────▼─────────┐
                 │  API GATEWAY     │
                 │  (FastAPI)       │
                 │  - Rate Limiting │
                 │  - Validation    │
                 │  - Audit         │
                 └────────┬─────────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
   ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
   │ AI Layer    │ │ OCR Layer   │ │ Export      │
   │ - Rules     │ │ - pdfplumber│ │ - Encrypted │
   │ - Local LLM │ │ - Tesseract │ │ - Plaintext │
   │ - Cloud AI* │ │ - PyMuPDF   │ │ - PDF       │
   └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
          │               │               │
          └───────────────┼───────────────┘
                          │
                 ┌────────▼─────────┐
                 │  SERVICE LAYER   │
                 │  - Ingestion     │
                 │  - Classification│
                 │  - Compliance    │
                 │  - Export        │
                 └────────┬─────────┘
                          │
                 ┌────────▼─────────┐
                 │  REPOSITORY LAYER│ ← NEW: all DB access here
                 │  (One per model) │
                 └────────┬─────────┘
                          │
                 ┌────────▼─────────┐
                 │  DATA LAYER      │
                 │  - SQLite/PG     │
                 │  - Local storage │
                 │  - S3 storage    │
                 │  - Encryption    │ ← NEW: at-rest encryption
                 └──────────────────┘

* Cloud AI = explicit user consent only, never default
```

---

## v1 → v2 Changes

| Component | v1 (Current) | v2 (Target) |
|---|---|---|
| **Auth** | None | Master password + session + auto-lock |
| **Encryption** | None | AES-256-GCM column-level, encrypted export packs |
| **Repository Layer** | Violated — routers use `db.execute()` | Enforced — all DB access through repositories |
| **AI Default** | `anthropic` (cloud) | `mock` (local-first) |
| **AI Strategy** | Single provider | Deterministic rules → Local LLM → Cloud AI (opt-in) |
| **OCR Strategy** | pdfplumber → Tesseract (no pre-processing) | PyMuPDF → pdfplumber → preprocessed Tesseract → advanced OCR |
| **Job Queue** | BackgroundTasks (ephemeral) | ARQ/Redis (persistent) |
| **Review States** | Boolean `needs_review` | Enum: draft → needs_user_review → user_confirmed / excluded / needs_agent |
| **Document States** | 14+ undocumented states | 9 defined states with user-facing display |
| **Export** | Plaintext JSON | Password-encrypted ZIP with PDF summary |
| **UX** | Admin tabs | Guided step workflow |
| **Pagination** | None | All list endpoints paginated |
| **Rate Limiting** | In-memory (state lost on restart) | SQLite/Redis backed |
| **Frontend** | Next.js SSR | PWA with offline support |

---

## Layer Description

### 1. Presentation Layer (Frontend)
- **Framework**: Next.js 14 App Router → PWA
- **State**: React hooks + `useReducer` per step (no global state manager needed)
- **Encryption**: Client-side key derivation (Argon2id), in-memory key only
- **Offline**: Service worker caching, offline page with status indicator
- **UI Design**: Calm, trustworthy, minimalist, document-focused (from spec)

### 2. Auth Gateway
- **Personal/Pro**: Master password → Argon2id → verify against stored hash
- **Team**: JWT with refresh tokens (future)
- **Session**: Server-side session table, configurable timeout, auto-lock on inactivity
- **Middleware**: Every request (except unlock/login) requires valid session

### 3. API Gateway (FastAPI)
- **Middleware stack**: CORS → Security Headers → Logging → Auth → Rate Limit → Input Validation
- **Rate Limiting**: Per-endpoint, per-IP, backed by SQLite
- **Input Validation**: Request body size limits, content-type enforcement, UUID validation
- **Audit**: All state changes → `audit_events` (append-only, no UPDATE/DELETE)

### 4. AI Layer
- **Provider chain**: `DeterministicProvider → OllamaProvider → AnthropicProvider → OpenAIProvider`
- **Fallback**: If provider A fails, try B (configurable chain order)
- **Data sovereignty**: Cloud providers require explicit user consent + visible indicator
- **Retry**: Exponential backoff, max 3 retries for transient errors
- **Shared code**: Prompt builder, JSON parser, ATO mapping — shared, not duplicated

### 5. OCR Layer
- **Layered strategy**: PyMuPDF (direct text) → pdfplumber (structured PDF) → Tesseract (image OCR with preprocessing)
- **Confidence gating**: Layer result accepted if confidence ≥ threshold (default 0.7)
- **Preprocessing**: Grayscale → binarization → deskew → contrast enhancement
- **Timeout**: Enforced per-layer via `asyncio.wait_for`

### 6. Service Layer
- **Ingestion Pipeline**: File → hash → dedup → OCR → classify → save items
- **Classification**: AI (or rules) → map to TaxItems → save with confidence
- **Compliance**: Rules-based (no AI needed) — risk, evidence, FY validation
- **Export**: Build package → encrypt → persist metadata → stream to user

### 7. Repository Layer (NEW)
- One repository class per model
- All `db.execute()` calls move here — routers and services never touch SQLAlchemy directly
- Repository methods return domain objects, not ORM instances (decoupling)

### 8. Data Layer
- **Database**: SQLite (personal/pro) / PostgreSQL (team)
- **Storage**: Local filesystem / S3-compatible
- **Encryption**: Application-level AES-256-GCM for PII fields
- **Backup**: Automated pg_dump or SQLite copy with rotation

---

## Data Flow

### Upload → Export (happy path)

```
User uploads PDF
  │
  ▼
POST /api/documents/upload
  │
  ├── Validate file (type, size, hash)
  ├── Create Document record (status: uploaded)
  ├── Create Job record (status: queued)
  ├── Start background task
  └── Return { document_id, job_id }
        │
        ▼
Background pipeline:
  │
  ├── 1. Hash dedup check (same session → duplicate_detected)
  ├── 2. Status: extracting_text
  ├── 3. OCR: PyMuPDF → pdfplumber → Tesseract (layered)
  ├── 4. Status: text_extracted
  ├── 5. Status: classifying
  ├── 6. Classify: Rules → Local LLM → Cloud AI (chain)
  ├── 7. Save ClassificationResult (encrypted)
  ├── 8. Create TaxItems (encrypted amounts)
  ├── 9. Status: classified / needs_review
  └── 10. Update Job: succeeded
        │
        ▼
User reviews items (frontend workflow step 3)
  │
  ├── Confirm item → review_status: user_confirmed
  ├── Exclude item → review_status: excluded_by_user
  ├── Flag for agent → review_status: needs_tax_agent_review
  └── All items reviewed? → Session status: review_complete
        │
        ▼
Export (frontend workflow step 4)
  │
  ├── User sets export password
  ├── Build package (items, evidence, documents)
  ├── Encrypt with AES-256-GCM
  ├── Persist export metadata (no data)
  └── Download encrypted ZIP
```

---

## Key Architectural Decisions

### ADR-001: Repository Pattern Enforced
All database queries move to `app/repositories/`. Routes and services import repositories, never `db.execute()`.

### ADR-002: Encryption at Application Layer
Encryption happens in Python, not at the database engine level. This keeps SQLite compatibility (sqlcipher is a separate product) and makes key rotation possible without DB migration.

### ADR-003: Cloud AI is Never Default
The default `ai_provider` is `mock`. To use cloud AI, the user must explicitly change config AND check a consent checkbox on first cloud-AI upload.

### ADR-004: Deterministic Rules > AI
Classification prioritizes deterministic keyword/regex matching first. AI is only consulted when rules can't determine a category. This is the reverse of the current architecture.

### ADR-005: Export Without Data Retention
Encrypted export packs are downloaded and stored by the user. The server persists only export metadata (timestamp, format, item count) — not the export data itself.

### ADR-006: Append-Only Audit
No UPDATE or DELETE on `audit_events`. All mutations write events. This is already implemented correctly.

---

## Technology Stack (Target)

| Layer | Current | Target | Rationale |
|---|---|---|---|
| **Backend** | FastAPI + SQLAlchemy async | Same | No change needed |
| **Database** | SQLite / PostgreSQL | Same + sqlcipher opt | Application-level encryption avoids engine lock-in |
| **OCR** | pdfplumber, Tesseract | + PyMuPDF, + Pillow preprocessing | Better text extraction, better image OCR |
| **AI** | Anthropic, OpenAI | + Deterministic rules, + Ollama, + llama.cpp | Local-first, no cloud dependency by default |
| **Job Queue** | FastAPI BackgroundTasks | + ARQ + Redis | Persistent queue, job recovery on crash |
| **Encryption** | None | + cryptography (AES-256-GCM) | Application-layer, portable |
| **Auth** | None | + argon2-cffi + secrets + itsdangerous | Master password for personal, JWT for team |
| **Frontend** | Next.js 14 | Same + PWA | SSR now, offline capability via service worker |
| **Containerization** | Docker Compose | Same + resource limits + secrets | Production hardening |
| **Caching** | None | + Redis (via ARQ) | Queue + rate limit backing |
