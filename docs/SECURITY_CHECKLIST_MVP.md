# Security Checklist (MVP)

## Authentication
- [x] Local master-password setup/unlock flow exists.
- [x] Session token hashing and revocation implemented.
- [x] Cookie policy is environment-aware (`Secure`/`HttpOnly`/`SameSite` configurable).
- [x] Production default is secure cookies; insecure local cookies require explicit opt-in.
- [x] DB-backed unlock capability checks added for sensitive routes (TTL + revocation + epoch).
- [x] Session/key epoch invalidation path exists for recovery reset and stale sessions.
- [ ] Multi-user/team RBAC is not in MVP scope.

## Export Encryption
- [x] Review pack export is encrypted with authenticated encryption.
- [x] Export password is validated server-side.
- [x] Password is never stored.
- [x] Export metadata stores hash/size/KDF fields only.

## Database and Storage
- [x] Field-level encryption-at-rest is partially implemented for selected sensitive text fields.
- [ ] Full database encryption-at-rest is not implemented yet.
- [x] Documents and exports stay on local storage by default.
- [ ] Secure file deletion guarantees are limited by filesystem behavior.

## Cloud AI Policy
- [x] Cloud AI remains optional and should be off unless explicitly enabled.
- [x] No default external document transfer in current workflow.

## Backup Handling
- [ ] Backup encryption policy depends on operator process.
- [x] Backup/restore manual runbook documented.

## Audit and Traceability
- [x] Audit events written for upload/review/export actions.
- [x] Workspace-scoped audit event API available.
- [x] Sensitive raw OCR/document content should not be logged in audit details.

## User Warnings
- [x] Recovery key is shown once and must be stored by user.
- [x] Export password warning indicates no recovery.

## Known Risks Before Real Use
- SQLite file exposure risk if host is compromised.
- No completed DB encryption-at-rest yet.
- Operator-dependent backup security.
- Legacy endpoints must remain disabled in production.
