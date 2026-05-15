# User Workflow v2 — Tax Return AI

## Workflow map
`Login/Unlock -> Tax Year Workspace -> Dashboard -> Documents -> Review Items -> Issues & Warnings -> Export Review Pack -> Settings/Security`

## 1) Login / Unlock
### User goal
Access the local workspace securely.

### Visible information
- Product disclaimer and non-lodgement boundary
- Workspace lock state
- Last unlock timestamp (if available)

### Primary actions
- Unlock with master password
- Start first-time setup
- Use recovery key path

### Empty state
- First run: no credentials configured yet

### Error state
- Invalid password
- Too many attempts / temporary lock

### Next recommended action
Complete unlock, then open Tax Year Workspace.

## 2) Tax Year Workspace
### User goal
Select or create the tax-year workspace to organize evidence.

### Visible information
- Workspace list by financial year
- Status badges and last updated timestamp
- Archive visibility toggle

### Primary actions
- Create workspace
- Open workspace
- Rename/archive/delete workspace (with confirmation)

### Empty state
- No workspace exists for any tax year

### Error state
- Workspace load failure
- Create/update conflict

### Next recommended action
Open a workspace and proceed to Dashboard.

## 3) Dashboard
### User goal
Understand current progress and what remains.

### Visible information
- Progress summary: documents, extracted items, review backlog
- Security mode: local-only vs cloud-AI-enabled
- Recent activity and unresolved issues count

### Primary actions
- Continue upload
- Jump to review queue
- Open unresolved issues

### Empty state
- Workspace exists but contains no documents/items yet

### Error state
- Summary panels fail to load

### Next recommended action
Go to Documents and upload evidence.

## 4) Documents
### User goal
Add and manage source evidence files.

### Visible information
- Upload constraints and supported formats
- Per-document processing state and duplicate signals
- Document metadata and preview access

### Primary actions
- Upload files (single/batch)
- Remove failed selections and retry
- Open document preview and extraction details

### Empty state
- No uploaded documents in workspace

### Error state
- Upload rejected, extraction failure, classification failure

### Next recommended action
When documents are extracted/classified, move to Review Items.

## 5) Review Items
### User goal
Confirm or exclude extracted evidence items before export.

### Visible information
- Item status, confidence, category, amount/description
- Evidence trace (source document/page/snippet where available)
- Review counters by status

### Primary actions
- Confirm item
- Exclude item
- Flag item for tax-agent review
- Edit item details with audit logging

### Empty state
- No items extracted yet

### Error state
- Item update conflict
- Missing source traceability

### Next recommended action
Resolve remaining draft/needs-review items and proceed to Issues & Warnings.

## 6) Issues & Warnings
### User goal
Resolve compliance and completeness blockers before export.

### Visible information
- Risk level and evidence completeness indicators
- Missing fields and unresolved questions
- Tax-agent referral triggers

### Primary actions
- Filter by severity/status
- Open linked item and resolve
- Mark issue resolved with note

### Empty state
- No issues/warnings detected

### Error state
- Compliance analysis unavailable

### Next recommended action
If no blocking issues remain, continue to Export Review Pack.

## 7) Export Review Pack
### User goal
Generate and download a secure evidence package.

### Visible information
- Export readiness and unresolved-item warnings
- Export format and encryption requirement
- Export history metadata

### Primary actions
- Set export password
- Generate encrypted review pack
- Download export artifact

### Empty state
- No previous exports for this workspace

### Error state
- Export generation failed
- Encryption or packaging failure

### Next recommended action
Download pack and hand off for human review.

## 8) Settings / Security
### User goal
Control security posture and privacy-related behavior.

### Visible information
- Session timeout and lock status
- Cloud AI consent status
- Data retention and deletion settings

### Primary actions
- Change master password
- Rotate/regenerate recovery key flow
- Configure session lock timeout
- Toggle cloud AI consent (with warnings)

### Empty state
- Security settings not initialized on first setup

### Error state
- Credential update failure
- Policy save failure

### Next recommended action
Return to Dashboard and continue workflow with updated security settings.
