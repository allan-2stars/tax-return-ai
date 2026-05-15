# Security Model v2 — tax-return-ai

> Target state. Current state has no auth, no encryption, and PII in plaintext.
> See AUDIT_AND_REDESIGN_PLAN.md for gap analysis.

---

## Security Principles

1. **Data sovereignty** — User data stays on user-controlled hardware by default. Cloud AI is opt-in.
2. **Encryption at rest** — All PII and financial data encrypted at the application layer.
3. **Encryption in transit** — HTTPS enforced (Cloudflare Tunnel already handles this).
4. **Minimal data retention** — Export data not persisted; document retention policies enforced.
5. **User-controlled keys** — Master password derived key never leaves memory.
6. **Append-only audit** — All security events logged, never modified.
7. **Secure by default** — No cloud AI, no telemetry, no external calls without explicit consent.

---

## Threat Model

### Assets to Protect

| Asset | Sensitivity | Location | Current Protection |
|---|---|---|---|
| **Uploaded documents** (PDF, images) | HIGH — TFNs, bank statements, payslips | Local filesystem or S3, paths in DB | None (plaintext storage) |
| **OCR-extracted text** | HIGH — names, addresses, ABNs, amounts | `document_pages.text`, `classification_results.raw_input` | None (plaintext DB) |
| **Tax items** (income, deductions) | HIGH — salary, expenses, categories | `tax_items.amount`, `tax_items.description` | None (plaintext DB) |
| **AI classification results** | MEDIUM — category assignments, confidence | `classification_results.*` | None (plaintext DB) |
| **Export packages** | HIGH — complete tax summary | `export_packages.export_data` | None (plaintext DB) |
| **Audit logs** | MEDIUM — event history, timestamps | `audit_events.details` | None (plaintext DB) |
| **AI API keys** | CRITICAL — Anthropic/OpenAI credentials | `.env` file | Plaintext env var |
| **Master password hash** | CRITICAL — gateway to all data | DB `app_settings` or dedicated table | None (not implemented) |

### Threat Actors

| Actor | Capability | Risk Level |
|---|---|---|
| **External attacker** (network access) | Can call all API endpoints, read/write all data | 🔴 **Critical** (no auth) |
| **Local attacker** (same machine) | Can read SQLite DB, uploaded files, env vars | 🔴 **Critical** (no encryption) |
| **Cloud AI provider** | Receives full document text | 🟠 **High** (opt-in required) |
| **Network eavesdropper** | Can observe traffic | 🟢 **Low** (HTTPS via Cloudflare) |
| **Compromised dependency** | Can exfiltrate data from process memory | 🟡 **Medium** (encryption keys in memory) |

---

## Security Architecture

### Layer 1: Network Security

```
Internet ──▶ Cloudflare Tunnel ──▶ localhost:8010 (backend)
                                ──▶ localhost:3020 (frontend)
```

- Backend binds to `127.0.0.1:8010` only (not publicly accessible)
- Frontend binds to `127.0.0.1:3020` only
- Cloudflare Tunnel provides HTTPS termination + DDoS protection
- CORS with explicit origins only (no wildcard)

### Layer 2: Authentication (Phase 2)

#### Personal/Pro Edition

```
┌────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ User   │───▶│ Enter Master │───▶│ Argon2id Key  │───▶│ Verify vs    │
│        │    │ Password     │    │ Derivation    │    │ Stored Hash  │
└────────┘    └──────────────┘    └──────────────┘    └──────┬───────┘
                                                             │
                                              ┌──────────────┘
                                              ▼
                                     ┌────────────────┐
                                     │ Create Session  │
                                     │ (server-side)   │
                                     │ + Enc Key in    │
                                     │   Memory        │
                                     └────────────────┘
```

- **First-time setup**: User creates master password → generate salt → Argon2id hash → store hash + salt
- **Recovery key**: Paper backup generated (base64-encoded 256-bit key), user must save
- **Login**: Enter password → Argon2id verify → server session with configurable TTL
- **Auto-lock**: Session expires after inactivity (default: 15 minutes) → in-memory encryption key wiped
- **No password reset**: If master password lost, use recovery key (resets password)

#### Team Edition (Future)
- JWT-based auth with refresh tokens
- Multi-tenant workspace isolation
- Role-based access control (owner, editor, viewer, tax_agent)

### Layer 3: Encryption at Rest (Phase 2)

#### Key Hierarchy

```
Master Password
      │
      ▼ (Argon2id)
Encryption Key (256-bit, in memory only)
      │
      ├── Encrypt/decrypt document pages
      ├── Encrypt/decrypt tax item amounts
      ├── Encrypt/decrypt classification results
      └── Encrypt/decrypt export data
```

#### Encrypted Fields

| Table | Column | Encryption | Notes |
|---|---|---|---|
| `document_pages` | `text` | AES-256-GCM | OCR-extracted text |
| `tax_items` | `amount` | AES-256-GCM | Numeric amount stored as encrypted string |
| `tax_items` | `description` | AES-256-GCM | Item description |
| `classification_results` | `raw_input` | AES-256-GCM | Full text sent to AI |
| `classification_results` | `raw_output` | AES-256-GCM | Raw AI response |
| `classification_results` | `parsed_output` | AES-256-GCM | Parsed classification JSON |
| `export_packages` | `export_data` | AES-256-GCM | Complete export payload |
| `review_actions` | `notes` | AES-256-GCM | Reviewer comments |
| `tax_session` | `notes` | AES-256-GCM | Session notes |
| `audit_events` | `details` | AES-256-GCM | Event details (consider if audit needs to be readable) |

**Decision**: Audit details should also be encrypted for consistency. Audit logs remain append-only and searchable by `entity_type` and `entity_id` but event JSON details are encrypted.

#### Implementation

```python
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

class FieldEncryptor:
    """Application-layer field encryption using AES-256-GCM."""
    
    def __init__(self, key: bytes):
        # key = Argon2id-derived 32 bytes
        self.aesgcm = AESGCM(key)
    
    def encrypt(self, plaintext: str) -> str:
        nonce = os.urandom(12)
        ct = self.aesgcm.encrypt(nonce, plaintext.encode(), None)
        return base64.b64encode(nonce + ct).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        raw = base64.b64decode(ciphertext)
        nonce, ct = raw[:12], raw[12:]
        return self.aesgcm.decrypt(nonce, ct, None).decode()
```

### Layer 4: Data in Transit

- **API calls**: HTTPS via Cloudflare Tunnel (already configured)
- **AI API calls**: HTTPS to Anthropic/OpenAI (existing, but data is plaintext to provider)
- **Mitigation for cloud AI**: Optional pre-encryption/redaction of PII before sending to AI

### Layer 5: Application Security

#### Current (v1)
| Measure | Status |
|---|---|
| CORS with explicit origins | ✅ Implemented |
| Security headers middleware | ✅ Implemented |
| Rate limiting | ✅ Implemented (bug fixed) |
| File type whitelist | ✅ Implemented |
| File size limit | ✅ Implemented |
| HTML sanitization | ✅ Implemented |
| Audit logging | ✅ Implemented |
| Structured logging | ✅ Implemented |

#### Target (v2 additions)
| Measure | Phase | Details |
|---|---|---|
| Authentication middleware | Phase 2 | Session-based, master password |
| Input validation middleware | Phase 8 | Body size, content-type, UUID format |
| SQL injection prevention | ✅ Already handled by SQLAlchemy | N/A |
| XSS prevention | ✅ React escape by default | N/A |
| CSRF protection | Phase 2 | Double-submit cookie or SameSite=Strict |
| Rate limit persistence | Phase 8 | SQLite-backed (survives restart) |
| Secure deletion | Phase 2 | Overwrite files on delete |
| Dependency scanning | Phase 8 | `pip-audit` in CI pipeline |

### Layer 6: Secure Export (Phase 6)

#### Export Flow

```
User clicks "Export" ──▶ Prompt for export password
                              │
                              ▼
                     AES-256-encrypt ZIP
                     │
                     ├── review-report.pdf (unencrypted? or password-protected)
                     ├── extracted-items.json.enc
                     ├── evidence-index.csv.enc
                     ├── source-documents/*.enc
                     └── metadata.json (unencrypted — contains FY, dates, format version)
                         └── "encryption": "AES-256-GCM"
                         └── "key_hint": "argon2id(export_password)"
                    
                     ──▶ Stream ZIP to browser
                     ──▶ Persist export metadata only (no export data)
```

The exported ZIP is decrypted on the user's machine — the server never has the plaintext export data after generation.

---

## Security Incident Response

### Data Breach Scenarios

| Scenario | Impact | Mitigation |
|---|---|---|
| **SQLite DB file stolen** | All PII and financial data readable | Encryption at rest makes data unreadable without master password |
| **API key leaked** | Attacker can use Anthropic/OpenAI with your account | Rotate key in `.env`, monitor provider dashboard for unusual usage |
| **Master password compromised** | Full data access + decryption | Recovery key allows password reset; all data is decryptable with old password |
| **AI provider data breach** | Document text sent to AI is leaked | Only applies to cloud AI users; consent checkbox makes this explicit risk acceptance |
| **Cloudflare Tunnel compromised** | Traffic can be intercepted | User's Cloudflare account security — outside our control |

### Logging and Monitoring

- All authentication attempts logged (success + failure)
- All encryption/decryption errors logged
- All export events logged (metadata only)
- All cloud AI usage logged (document count, size, provider)
- Configurable alert threshold for failed auth attempts

---

## Compliance Considerations

### Australian Privacy Principles (APPs)

| Principle | Compliance | Status |
|---|---|---|
| APP 1 — Open management of personal info | Privacy policy | Not yet drafted |
| APP 3 — Collection of solicited information | Only collects what user uploads | ✅ Current |
| APP 4 — Dealing with unsolicited information | Hash dedup prevents duplicates | ✅ Current |
| APP 6 — Use or disclosure of personal info | Cloud AI option requires consent | ❌ Phase 7 |
| APP 11 — Security of personal information | Encryption at rest | ❌ Phase 2 |
| APP 12 — Access to personal information | Export feature | ✅ Current |

### ATO Requirements (Tax Agent Use)
- Tax agent records must be retained for 5 years
- Data must be stored within Australia (or with explicit consent for offshore processing)
- Records must be recoverable
- These only apply to `team` edition — `personal` edition is for individual use

---

## Default Configuration (Security-Conscious)

| Setting | Current Default | Target Default | Rationale |
|---|---|---|---|
| `ai_provider` | `anthropic` | `mock` | No cloud by default |
| `ocr_provider` | `pdfplumber` | `pdfplumber` | ✅ Local, no change needed |
| `telemetry_enabled` | `false` | `false` | ✅ Already correct |
| `edition` | `personal` | `personal` | ✅ Already correct |
| `redact_sensitive_logs` | `true` | `true` | ✅ Already correct |
| `max_upload_size_mb` | `20` | `20` | ✅ Reasonable default |
| Session timeout | N/A | 15 minutes | Added in Phase 2 |
| Login required | No | Yes (personal edition) | Added in Phase 2 |
| Data retention days | N/A | 365 days (auto-archive) | Added in Phase 3 |
