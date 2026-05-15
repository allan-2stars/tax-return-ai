# Data Model v2 — tax-return-ai

> Target state after all rebuild phases. New tables and columns marked with ✦.

---

## Tables

### tax_sessions — Groups documents for one user + one financial year

| Column | Type | v1 | v2 Changes |
|---|---|---|---|
| `id` | UUID PK | ✅ | ✅ |
| `user_id` | UUID FK → users | ❌ | **NEW ✦** — multi-user isolation |
| `title` | String(200) | ✅ | ✅ |
| `financial_year` | String(9) | ✅ | ✅ |
| `status` | String(30) | ✅ | ✅ (values: `draft`, `importing`, `reviewing`, `ready_for_export`, `exported`, `archived`) |
| `notes` | Text | ✅ | ✅ (encrypted) |
| `encryption_key_id` | String | ❌ | **NEW ✦** — key version for at-rest encryption |
| `soft_deleted_at` | DateTime | ❌ | **NEW ✦** — recoverable deletion |
| `retention_days` | Integer | ❌ | **NEW ✦** — override global retention policy |
| `expires_at` | DateTime | ❌ | **NEW ✦** — auto-archive/delete threshold |
| `created_at` | DateTime | ✅ | ✅ |
| `updated_at` | DateTime | ✅ | ✅ |

---

### documents — Uploaded file metadata

| Column | Type | v1 | v2 Changes |
|---|---|---|---|
| `id` | UUID PK | ✅ | ✅ |
| `session_id` | UUID FK → tax_sessions | ✅ | ✅ |
| `original_filename` | String(500) | ✅ | ✅ |
| `mime_type` | String(100) | ✅ | ✅ |
| `file_size_bytes` | Integer | ✅ | ✅ |
| `file_hash` | String(64) | ✅ | ✅ — SHA-256 |
| `storage_path` | String(500) | ✅ | ✅ |
| `storage_backend` | String(20) | ❌ | **NEW ✦** — 'local' or 's3' |
| `category` | String(50) | ✅ | ✅ |
| `ocr_strategy` | String(50) | ❌ | **NEW ✦** — 'pymupdf', 'pdfplumber', 'tesseract', 'mock' |
| `financial_year` | String(9) | ✅ | ✅ |
| `status` | String(30) | ✅ | ✅ — 9 canonical states (see doc lifecycle doc) |
| `status_reason` | Text | ✅ | ✅ |
| `soft_deleted_at` | DateTime | ❌ | **NEW ✦** — recoverable deletion |
| `created_at` | DateTime | ✅ | ✅ |
| `updated_at` | DateTime | ✅ | ✅ |

---

### document_pages — Per-page OCR text

| Column | Type | v1 | v2 Changes |
|---|---|---|---|
| `id` | UUID PK | ✅ | ✅ |
| `document_id` | UUID FK → documents | ✅ | ✅ |
| `page_number` | Integer | ✅ | ✅ |
| `text` | Text | ✅ → encrypted | **CHANGED ✦** — `encrypted_text` (AES-256-GCM) |
| `confidence` | Float | ✅ | ✅ |
| `ocr_method` | String(50) | ✅ | ✅ |
| `created_at` | DateTime | ✅ | ✅ |

---

### tax_items — Classified line items (canonical product row)

| Column | Type | v1 | v2 Changes |
|---|---|---|---|
| `id` | UUID PK | ✅ | ✅ |
| `session_id` | UUID FK → tax_sessions | ✅ | ✅ |
| `item_type` | String(20) | ✅ | ✅ — 'income' or 'deduction' |
| `category` | String(50) | ✅ | ✅ — reference `app/constants/categories.py` |
| `amount` | Float / encrypted | ✅ → encrypted | **CHANGED ✦** — `encrypted_amount` (AES-256-GCM) |
| `description` | Text | ✅ → encrypted | **CHANGED ✦** — `encrypted_description` (AES-256-GCM) |
| `confidence` | Float | ✅ | ✅ |
| `review_status` | String(30) | ❌ (was `needs_review` bool) | **NEW ✦** — `draft`, `needs_user_review`, `user_confirmed`, `excluded_by_user`, `needs_tax_agent_review` |
| `review_reason` | Text | ✅ | ✅ |
| `reviewed_at` | DateTime | ✅ | ✅ |
| `reviewed_by` | String(100) | ✅ | ✅ |
| `ato_reference_hint` | Text | ✅ | ✅ |
| `source_document_id` | UUID FK → documents | via DocumentItem | **NEW ✦** — direct FK (denormalize for performance) |
| `financial_year` | String(9) | ✅ | ✅ |
| `soft_deleted_at` | DateTime | ❌ | **NEW ✦** |
| `created_at` | DateTime | ✅ | ✅ |
| `updated_at` | DateTime | ✅ | ✅ |

---

### document_items — Join table (document → items)

| Column | Type | v1 | v2 Changes |
|---|---|---|---|
| `id` | UUID PK | ✅ | ✅ |
| `document_id` | UUID FK → documents | ✅ | ✅ |
| `item_id` | UUID FK → tax_items | ✅ | ✅ |
| `page_number` | Integer | ✅ | ✅ |
| `snippet` | Text | ✅ | ✅ |
| `ocr_confidence` | Float | ✅ | ✅ |
| `created_at` | DateTime | ✅ | ✅ |

---

### classification_results — Raw AI output per classification run

| Column | Type | v1 | v2 Changes |
|---|---|---|---|
| `id` | UUID PK | ✅ | ✅ |
| `document_id` | UUID FK → documents | ✅ | ✅ |
| `session_id` | UUID FK → tax_sessions | ✅ | ✅ |
| `raw_input` | Text | ✅ → encrypted | **CHANGED ✦** — `encrypted_raw_input` |
| `raw_output` | Text | ✅ → encrypted | **CHANGED ✦** — `encrypted_raw_output` |
| `parsed_output` | JSON | ✅ → encrypted | **CHANGED ✦** — `encrypted_parsed_output` |
| `confidence` | Float | ✅ | ✅ |
| `provider` | String(50) | ✅ | ✅ |
| `model` | String(100) | ✅ | ✅ |
| `strategy` | String(20) | ❌ | **NEW ✦** — `deterministic`, `local_ai`, `cloud_ai` |
| `timing_ms` | Integer | ✅ | ✅ |
| `created_at` | DateTime | ✅ | ✅ |

---

### review_actions — Append-only user review events

| Column | Type | v1 | v2 Changes |
|---|---|---|---|
| `id` | UUID PK | ✅ | ✅ |
| `item_id` | UUID FK → tax_items | ✅ | ✅ |
| `user_id` | UUID FK → users | ❌ | **NEW ✦** |
| `action` | String(30) | ✅ | ✅ — 'confirmed', 'excluded', 'flagged', 'amount_edited', 'description_edited' |
| `previous_status` | String(30) | ✅ | ✅ |
| `new_status` | String(30) | ✅ | ✅ |
| `notes` | Text | ✅ → encrypted | **CHANGED ✦** — `encrypted_notes` |
| `source` | String(20) | ✅ | ✅ — 'user' or 'system' or 'agent' |
| `created_at` | DateTime | ✅ | ✅ |

---

### export_packages — Generated export metadata (NOT export data)

| Column | Type | v1 | v2 Changes |
|---|---|---|---|
| `id` | UUID PK | ✅ | ✅ |
| `session_id` | UUID FK → tax_sessions | ✅ | ✅ |
| `format` | String(20) | ✅ | ✅ — 'encrypted_zip', 'json', 'csv' |
| `item_count` | Integer | ✅ | ✅ |
| `total_amount` | Float | ✅ | ✅ (encrypted or aggregated — TBD) |
| `total_taxable` | Float | ✅ | ✅ |
| `compliance_score` | String(20) | ✅ | ✅ |
| `export_data` | Text | ✅ → REMOVED | **REMOVED ✦** — export data is no longer persisted; replaced with metadata-only record |
| `encryption_method` | String(30) | ❌ | **NEW ✦** — 'aes-256-gcm', 'none' |
| `file_size_bytes` | Integer | ❌ | **NEW ✦** — export pack size before download |
| `created_at` | DateTime | ✅ | ✅ |

---

### jobs — Long-running job tracking

| Column | Type | v1 | v2 Changes |
|---|---|---|---|
| `id` | UUID PK | ✅ | ✅ |
| `session_id` | UUID FK → tax_sessions | ✅ | ✅ |
| `document_id` | UUID FK → documents | ✅ | ✅ |
| `job_type` | String(30) | ✅ | ✅ — 'ingestion', 'classification', 'export' |
| `status` | String(20) | ✅ | ✅ — 'queued', 'running', 'succeeded', 'failed', 'cancelled', 'retrying' |
| `progress` | Float | ✅ | ✅ |
| `progress_message` | Text | ✅ | ✅ |
| `error_message` | Text | ✅ | ✅ (truncate to 500 chars, redact paths) |
| `result_summary` | JSON | ✅ | ✅ |
| `worker_id` | String(50) | ❌ | **NEW ✦** — ARQ worker ID for persistent queue |
| `queued_at` | DateTime | ✅ | ✅ |
| `started_at` | DateTime | ✅ | ✅ |
| `completed_at` | DateTime | ✅ | ✅ |
| `created_at` | DateTime | ✅ | ✅ |
| `updated_at` | DateTime | ✅ | ✅ |

---

### audit_events — Append-only event log

| Column | Type | v1 | v2 Changes |
|---|---|---|---|
| `id` | UUID PK | ✅ | ✅ |
| `entity_type` | String(50) | ✅ | ✅ |
| `entity_id` | String(36) | ✅ | ✅ |
| `event_type` | String(30) | ✅ | ✅ |
| `details` | JSON | ✅ → encrypted | **CHANGED ✦** — `encrypted_details` (consider if search needs plaintext) |
| `user_id` | UUID FK → users | ❌ | **NEW ✦** |
| `ip_address` | String(45) | ❌ | **NEW ✦** — source IP for security events |
| `user_agent` | String(200) | ❌ | **NEW ✦** — client identifier |
| `created_at` | DateTime | ✅ | ✅ |

---

### app_settings — Runtime key/value configuration

| Column | Type | v1 | v2 Changes |
|---|---|---|---|
| `key` | String(100) PK | ✅ | ✅ |
| `value` | Text | ✅ | ✅ |
| `encrypted` | Boolean | ❌ | **NEW ✦** — if true, value is encrypted |
| `updated_at` | DateTime | ✅ | ✅ |

---

### ✦ users — NEW table (multi-user support)

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `email` | String(255) | Unique, nullable for personal edition |
| `display_name` | String(100) | |
| `password_hash` | String(255) | Argon2id hash |
| `password_salt` | String(64) | Random salt per user |
| `recovery_key_hash` | String(255) | For password reset |
| `recovery_key_salt` | String(64) | |
| `edition` | String(20) | 'personal', 'pro', 'team' |
| `is_active` | Boolean | |
| `last_login_at` | DateTime | |
| `created_at` | DateTime | |
| `updated_at` | DateTime | |

---

### ✦ sessions — NEW table (server-side auth sessions)

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | Session token |
| `user_id` | UUID FK → users | |
| `encryption_key` | BLOB | Argon2id-derived key, stored only during session lifetime |
| `ip_address` | String(45) | |
| `user_agent` | String(200) | |
| `expires_at` | DateTime | Auto-lock timeout |
| `last_activity_at` | DateTime | For idle timeout |
| `created_at` | DateTime | |

---

### ✦ workspaces — NEW table (team edition)

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `name` | String(200) | |
| `owner_id` | UUID FK → users | |
| `edition` | String(20) | |
| `settings` | JSON | Workspace-level config |
| `created_at` | DateTime | |
| `updated_at` | DateTime | |

### ✦ workspace_members — NEW table (team edition)

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `workspace_id` | UUID FK → workspaces | |
| `user_id` | UUID FK → users | |
| `role` | String(20) | 'owner', 'editor', 'viewer', 'tax_agent' |
| `invited_at` | DateTime | |
| `joined_at` | DateTime | |
| `created_at` | DateTime | |

---

## Entity-Relationship Diagram

```
users ──┐
         │
         ├── owns → workspaces ──┐
         │                       │
         ├── member_of ──────────┤ workspace_members
         │                       │
         ├── owns → tax_sessions ──────┐
         │                             │
         │                             ├── has → documents ────────┐
         │                             │     │                     │
         │                             │     ├── has → document_pages
         │                             │     │
         │                             │     ├── classified_by → classification_results
         │                             │     │
         │                             │     └── linked_to → document_items ──┐
         │                             │                                      │
         │                             ├── has → tax_items ──────────────────┘
         │                             │     │
         │                             │     ├── reviewed_by → review_actions
         │                             │     └── exported_in → export_packages
         │                             │
         │                             └── has → jobs
         │
         └── has → sessions (auth)
                         │
                         └──→ audit_events
```

---

## v1 → v2 Migration

### Schema Changes

| Change | Type | Migration |
|---|---|---|
| `tax_sessions.user_id` | NEW column | Add FK, backfill with default user for existing data |
| `tax_sessions.encryption_key_id` | NEW column | Nullable, populated on first encrypt |
| `tax_sessions.soft_deleted_at` | NEW column | Nullable, existing rows remain NULL |
| `tax_sessions.expires_at` | NEW column | Nullable |
| `tax_sessions.retention_days` | NEW column | Default to 365 |
| `documents.ocr_strategy` | NEW column | Nullable, backfill from v1 logic |
| `documents.storage_backend` | NEW column | Default 'local' |
| `documents.soft_deleted_at` | NEW column | Nullable |
| `document_pages.text` → `encrypted_text` | RENAME + encrypt | Read existing plaintext → encrypt → write → drop old |
| `tax_items.amount` → `encrypted_amount` | RENAME + encrypt | Same approach |
| `tax_items.description` → `encrypted_description` | RENAME + encrypt | Same approach |
| `tax_items.needs_review` → `review_status` | COLUMN TYPE CHANGE | Boolean → enum migration (True → needs_user_review, False → user_confirmed) |
| `tax_items.source_document_id` | NEW column | Nullable, populated from DocumentItem join |
| `tax_items.soft_deleted_at` | NEW column | Nullable |
| `classification_results.*_output` → `encrypted_*` | RENAME + encrypt | Multiple column rename |
| `classification_results.strategy` | NEW column | Nullable |
| `review_actions.notes` → `encrypted_notes` | RENAME + encrypt | |
| `review_actions.user_id` | NEW column | Nullable |
| `export_packages.export_data` | DROP column | Data migration: read → encrypt → write to file → remove column |
| `export_packages.encryption_method` | NEW column | Default 'none' for v1 exports |
| `export_packages.file_size_bytes` | NEW column | Nullable |
| `jobs.worker_id` | NEW column | Nullable |
| `audit_events.details` → `encrypted_details` | RENAME + encrypt | Optional — depends on audit searchability requirements |
| `audit_events.user_id` | NEW column | Nullable |
| `audit_events.ip_address` | NEW column | Nullable |
| `audit_events.user_agent` | NEW column | Nullable |
| `app_settings.encrypted` | NEW column | Default false |
| Add `users` table | NEW | |
| Add `sessions` table | NEW | |
| Add `workspaces` table | NEW | |
| Add `workspace_members` table | NEW | |

### Migration Strategy

1. Add new nullable columns first (no data loss)
2. Backfill data: read plaintext → encrypt → write to encrypted column
3. Add NOT NULL constraints where applicable
4. Drop old plaintext columns
5. Add unique constraints, FK constraints
6. Run migration in deploy without downtime (add before remove)

### Data Encryption Migration

```python
# Pseudo-code for encrypting existing data
async def migrate_to_encryption(db, encryptor):
    # 1. document_pages.text → encrypted_text
    pages = await db.execute(select(DocumentPage))
    for page in pages:
        if page.text:
            page.encrypted_text = encryptor.encrypt(page.text)
            page.text = None  # or drop column after migration
    
    # 2. tax_items.amount → encrypted_amount
    items = await db.execute(select(TaxItem))
    for item in items:
        if item.amount is not None:
            item.encrypted_amount = encryptor.encrypt(str(item.amount))
            item.amount = None
    
    # 3. tax_items.needs_review → review_status
    for item in items:
        if item.amount is not None:
            item.review_status = "needs_user_review" if item.needs_review else "user_confirmed"
    
    await db.commit()
```

---

## Indexes

| Table | Index | v1 | v2 |
|---|---|---|---|
| `tax_sessions` | `user_id` | ❌ | **NEW** |
| `tax_sessions` | `status` | ✅ | ✅ |
| `tax_sessions` | `financial_year` | ✅ | ✅ |
| `tax_sessions` | `soft_deleted_at` | ❌ | **NEW** (filtered) |
| `documents` | `session_id` | ✅ | ✅ |
| `documents` | `file_hash` | ✅ | ✅ |
| `documents` | `session_id + file_hash` | ✅ | ✅ (dedup query) |
| `documents` | `status` | ✅ | ✅ |
| `documents` | `soft_deleted_at` | ❌ | **NEW** (filtered) |
| `document_pages` | `document_id + page_number` | ✅ | ✅ |
| `tax_items` | `session_id` | ✅ | ✅ |
| `tax_items` | `review_status` | ❌ | **NEW** |
| `tax_items` | `item_type + session_id` | ✅ | ✅ |
| `classification_results` | `document_id` | ✅ | ✅ |
| `jobs` | `session_id` | ✅ | ✅ |
| `jobs` | `status` | ✅ | ✅ |
| `export_packages` | `session_id` | ✅ | ✅ |
| `audit_events` | `entity_type + entity_id` | ✅ | ✅ |
| `audit_events` | `created_at` | ✅ | ✅ |
| `audit_events` | `user_id` | ❌ | **NEW** |
| `sessions` | `user_id` | ❌ | **NEW** |
| `sessions` | `expires_at` | ❌ | **NEW** |
| `workspace_members` | `workspace_id + user_id` | ❌ | **NEW** (unique) |
