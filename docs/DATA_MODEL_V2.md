# Data Model v2 — Target Definition (No Migration Yet)

This document defines the target Phase 1 data model for Tax Return AI.
It is a design specification only. No migration is executed in this phase.

## Design goals
- Local-first confidential document handling
- Explicit authentication/session boundary for all workspaces
- Review-first item lifecycle with traceable status transitions
- Encryption-aware metadata and auditable security events

## Entities

## 1) User
Purpose: local account identity for unlocking and ownership.

Fields:
- `id` (UUID, PK)
- `email` (string, nullable for personal edition)
- `display_name` (string)
- `master_password_hash` (string)
- `master_password_salt` (string)
- `recovery_key_hash` (string)
- `is_active` (boolean)
- `created_at` (datetime)
- `updated_at` (datetime)
- `last_login_at` (datetime, nullable)

Relations:
- One `User` to many `AuthSession`
- One `User` to many `TaxWorkspace`
- One `User` to many `ReviewAction`
- One `User` to many `AuditEvent`

## 2) AuthSession
Purpose: lock/unlock session state and inactivity controls.

Fields:
- `id` (UUID, PK)
- `user_id` (UUID, FK -> User)
- `status` (string: active/locked/expired/revoked)
- `created_at` (datetime)
- `last_activity_at` (datetime)
- `expires_at` (datetime)
- `locked_at` (datetime, nullable)
- `ip_address` (string, nullable)
- `user_agent` (string, nullable)

Relations:
- Many `AuthSession` to one `User`

## 3) TaxWorkspace
Purpose: tax-year container for documents, items, issues, and exports.

Fields:
- `id` (UUID, PK)
- `user_id` (UUID, FK -> User)
- `title` (string)
- `financial_year` (string, e.g., `2025-2026`)
- `status` (string: draft/in_review/ready_for_export/exported/archived)
- `notes` (encrypted text, nullable)
- `created_at` (datetime)
- `updated_at` (datetime)
- `archived_at` (datetime, nullable)

Relations:
- Many `TaxWorkspace` to one `User`
- One `TaxWorkspace` to many `Document`
- One `TaxWorkspace` to many `ExtractedItem`
- One `TaxWorkspace` to many `ReviewIssue`
- One `TaxWorkspace` to many `ExportPackage`
- One `TaxWorkspace` to many `AuditEvent`

## 4) Document
Purpose: uploaded source document metadata and lifecycle state.

Fields:
- `id` (UUID, PK)
- `workspace_id` (UUID, FK -> TaxWorkspace)
- `original_filename` (string)
- `mime_type` (string)
- `file_size_bytes` (integer)
- `file_hash_sha256` (string)
- `storage_backend` (string: local/s3)
- `storage_path` (string)
- `status` (DocumentStatus enum)
- `status_reason` (string, nullable)
- `created_at` (datetime)
- `updated_at` (datetime)
- `deleted_at` (datetime, nullable)

Relations:
- Many `Document` to one `TaxWorkspace`
- One `Document` to many `DocumentPage`
- One `Document` to many `ExtractedItem`
- One `Document` to many `ReviewIssue`

## 5) DocumentPage
Purpose: page-level extraction output and traceability.

Fields:
- `id` (UUID, PK)
- `document_id` (UUID, FK -> Document)
- `page_number` (integer)
- `extracted_text` (encrypted text)
- `ocr_method` (string)
- `ocr_confidence` (float, nullable)
- `created_at` (datetime)

Relations:
- Many `DocumentPage` to one `Document`

## 6) ExtractedItem
Purpose: candidate tax evidence item derived from document text.

Fields:
- `id` (UUID, PK)
- `workspace_id` (UUID, FK -> TaxWorkspace)
- `document_id` (UUID, FK -> Document)
- `document_page_id` (UUID, FK -> DocumentPage, nullable)
- `item_type` (string: income/deduction/out_of_scope/needs_review)
- `category` (string)
- `amount` (encrypted numeric/text, nullable)
- `description` (encrypted text, nullable)
- `confidence` (float, nullable)
- `status` (ExtractedItemStatus enum)
- `status_reason` (string, nullable)
- `source_snippet` (encrypted text, nullable)
- `created_at` (datetime)
- `updated_at` (datetime)

Relations:
- Many `ExtractedItem` to one `TaxWorkspace`
- Many `ExtractedItem` to one `Document`
- Many `ExtractedItem` to one `DocumentPage` (optional)
- One `ExtractedItem` to many `ReviewAction`
- One `ExtractedItem` to many `ReviewIssue`

## 7) ReviewAction
Purpose: append-only history of item/user review decisions.

Fields:
- `id` (UUID, PK)
- `workspace_id` (UUID, FK -> TaxWorkspace)
- `item_id` (UUID, FK -> ExtractedItem)
- `user_id` (UUID, FK -> User)
- `action_type` (string)
- `from_status` (ExtractedItemStatus enum, nullable)
- `to_status` (ExtractedItemStatus enum)
- `notes` (encrypted text, nullable)
- `created_at` (datetime)

Relations:
- Many `ReviewAction` to one `TaxWorkspace`
- Many `ReviewAction` to one `ExtractedItem`
- Many `ReviewAction` to one `User`

## 8) ReviewIssue
Purpose: unresolved warnings/questions that block clean export.

Fields:
- `id` (UUID, PK)
- `workspace_id` (UUID, FK -> TaxWorkspace)
- `document_id` (UUID, FK -> Document, nullable)
- `item_id` (UUID, FK -> ExtractedItem, nullable)
- `issue_code` (string)
- `severity` (string: low/medium/high)
- `title` (string)
- `detail` (text)
- `status` (string: open/resolved/dismissed)
- `resolved_at` (datetime, nullable)
- `resolved_by_user_id` (UUID, FK -> User, nullable)
- `created_at` (datetime)

Relations:
- Many `ReviewIssue` to one `TaxWorkspace`
- Many `ReviewIssue` to one `Document` (optional)
- Many `ReviewIssue` to one `ExtractedItem` (optional)

## 9) ExportPackage
Purpose: export lifecycle metadata and secure-package references.

Fields:
- `id` (UUID, PK)
- `workspace_id` (UUID, FK -> TaxWorkspace)
- `status` (ExportStatus enum)
- `format` (string: encrypted_zip/json/csv)
- `encryption_method` (string, nullable)
- `item_count` (integer)
- `file_size_bytes` (integer, nullable)
- `download_count` (integer, default 0)
- `last_downloaded_at` (datetime, nullable)
- `failure_reason` (text, nullable)
- `created_at` (datetime)
- `updated_at` (datetime)
- `deleted_at` (datetime, nullable)

Relations:
- Many `ExportPackage` to one `TaxWorkspace`

## 10) AuditEvent
Purpose: append-only security and business event log.

Fields:
- `id` (UUID, PK)
- `workspace_id` (UUID, FK -> TaxWorkspace, nullable)
- `user_id` (UUID, FK -> User, nullable)
- `entity_type` (string)
- `entity_id` (string)
- `event_type` (string)
- `event_details` (encrypted JSON/text, nullable)
- `ip_address` (string, nullable)
- `user_agent` (string, nullable)
- `created_at` (datetime)

Relations:
- Many `AuditEvent` to one `TaxWorkspace` (optional)
- Many `AuditEvent` to one `User` (optional)

## 11) EncryptionKeyMetadata
Purpose: key lifecycle metadata without storing plaintext key material.

Fields:
- `id` (UUID, PK)
- `user_id` (UUID, FK -> User)
- `key_version` (integer)
- `kdf_algorithm` (string, e.g., argon2id)
- `kdf_params` (JSON/text)
- `key_fingerprint` (string)
- `status` (string: active/rotating/retired)
- `created_at` (datetime)
- `retired_at` (datetime, nullable)

Relations:
- Many `EncryptionKeyMetadata` to one `User`

## Required enums

## DocumentStatus
- `uploaded`
- `extracting_text`
- `text_extracted`
- `classifying`
- `classified`
- `needs_review`
- `reviewed`
- `included_in_report`
- `archived`
- `deleted`

## ExtractedItemStatus
- `draft`
- `needs_review`
- `confirmed`
- `excluded`
- `tax_agent_review`

## ExportStatus
- `draft`
- `generating`
- `ready`
- `failed`
- `downloaded`
- `deleted`

## Notes for implementation sequencing
- Preserve existing tables as scaffolding and migrate incrementally.
- Keep OCR and AI provider behavior unchanged in this phase.
- Keep Docker Compose topology unchanged in this phase.
