# Security Model v2 — Tax Return AI

## Security baseline
- Local-first by default
- Confidential document handling by default
- Explicit consent before any cloud transmission
- Defense-in-depth across auth, encryption, session controls, and audit

## 1) Master password model
- First-run setup requires master password creation
- Password is never stored in plaintext
- Store only Argon2id hash + per-user salt + versioned KDF parameters
- Master password derives runtime data-encryption key material for active session use
- Unlock is required before any workspace/document access

## 2) Recovery key model
- Recovery key generated once at setup as high-entropy secret
- Store only a hash of recovery key in database
- Recovery key is shown once and must be user-saved offline
- Recovery flow resets master password after successful verification
- Recovery events are always audited

## 3) Session lock model
- Unlock creates short-lived auth session record
- Inactivity timeout auto-locks workspace and invalidates session
- Manual lock is available from UI at all times
- Session extension requires valid recent activity and policy checks
- Lock/unlock events are appended to audit trail

## 4) Encryption at rest target
- Target: AES-256-GCM application-layer encryption for sensitive payload fields
- Scope includes OCR text, extracted item details, AI raw payloads, review notes, export metadata payload fields requiring confidentiality
- Key hierarchy must support key rotation metadata and backward decryption for old records
- Plaintext persistence of sensitive fields is out-of-policy target state

## 5) Encrypted export target
- Default export format is encrypted review pack
- User must provide export password at generation time
- Server stores export metadata only; full plaintext export payload should not be retained by default target design
- Export lifecycle states must be auditable

## 6) Cloud AI consent rules
- Cloud AI usage is disabled by default
- Enabling cloud AI requires explicit, informed user consent
- Consent must be reversible and clearly visible in UI state
- Consent records are audited with timestamp and actor
- Per-request safeguards must block accidental external transmission when consent is absent

## 7) Data that must never be sent externally by default
- Raw uploaded documents
- Full OCR page text
- Full extracted item ledger
- User-entered notes and review rationale
- Export artifacts and package contents
- Recovery key or derived key material

## 8) Secure deletion future design
- Define deletion policies for documents, derived text, exports, and logs
- Support soft-delete markers for user recovery window where policy allows
- Implement secure wipe strategy for local file artifacts after retention expiry
- Keep deletion actions and policy decisions in append-only audit events

## 9) Audit log principles
- Append-only audit events; no in-place mutation of historical events
- Capture actor, action, entity, timestamp, and minimal required context
- Audit events must be tamper-evident by process and schema constraints
- Security-sensitive actions (unlock, lock, recovery, export, consent change, deletion) require explicit event records

## 10) Phase boundaries
### In phase now (Phase 1 definition)
- Finalize security requirements and information architecture
- Define target entities and policies

### Not changing yet
- No provider-level OCR/AI logic changes
- No Docker Compose topology changes
- No irreversible migration execution
