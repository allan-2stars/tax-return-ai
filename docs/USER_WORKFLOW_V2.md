# User Workflow v2 — tax-return-ai

> Target UX after Phase 1 redesign. Calm, guided, trustworthy.

---

## Workflow Overview

```
 ┌──────────────────────────────────────────────────────────────────┐
 │  Step 1     Step 2         Step 3         Step 4        Complete │
 │  Unlock ──▶ Select ──────▶ Upload ──────▶ Review ──────▶ Export  │
 │  🔒        📁 Tax Year    📄 Documents   ✅ Items       📦 Pack │
 └──────────────────────────────────────────────────────────────────┘
                    Progress indicator always visible
```

Each step is a distinct page/view with clear "Next" / "Back" navigation. No confusing tabs. No hidden features.

---

## Step 0 — Unlock Screen

**When**: First visit / session expired

| Element | Description |
|---|---|
| **Logo** | "tax-return-ai" with lock icon |
| **Password field** | Master password input (type=password) |
| **Submit button** | "Unlock Workspace" |
| **First-time link** | "Set up your workspace" (runs initial setup) |
| **Recovery link** | "Lost password? Use recovery key" |
| **Security indicator** | 🔒 Data stays on your device / AES-256 encrypted |
| **Status message** | Error on wrong password, auto-lock notice |

### States
- **First run**: No hash stored → show setup wizard (create password, save recovery key)
- **Locked**: Password prompt, session timeout display
- **Error**: "Incorrect password. X attempts remaining." (optional rate limit)

---

## Step 1 — Select Tax Year

**When**: Workspace unlocked

| Element | Description |
|---|---|
| **Heading** | "Welcome back, [user]" or "New Tax Season" |
| **Subtitle** | "Select a session to continue, or start a new one." |
| **Existing sessions** | List of recent sessions with status badge (Draft / In Review / Complete) |
| **New session button** | "+ New Tax Year" → creates fresh session |
| **Session card** | Title, FY, document count, item count, last updated |
| **Archive toggle** | Show/hide archived sessions |
| **Security badge** | 🔒 Local / ☁️ Cloud AI mode indicator |

### UX Notes
- Most recent session at top
- Sessions grouped by status (active vs archived)
- Empty state: "You haven't created any sessions yet. Start by selecting a tax year."

---

## Step 2 — Upload Documents

**When**: Session selected or created

| Element | Description |
|---|---|
| **Step indicator** | "Step 2 of 4 — Upload Documents" |
| **Session info** | "FY 2025-2026 · {session title}" |
| **Upload area** | Drag-drop zone with dashed border, click to browse |
| **File list** | Selected files with preview, type icon, size, remove button |
| **Upload button** | "Upload & Process" (disabled when no files selected) |
| **Batch progress** | Per-file progress (queued → processing → done/error) |
| **Existing documents** | List of already-uploaded documents with status |
| **AI indicator** | 🔒 Local processing / ☁️ Cloud AI (consent checkbox if cloud) |
| **Back button** | ← Change tax year |
| **Skip/Next** | Proceeds to review even without new uploads |

### States
- **Empty**: Large drag-drop zone, "Drop your PDFs, images, or bank statements here"
- **Files selected**: File cards appear with thumbnails, total size
- **Uploading**: Progress bars per file, animated checkmarks on completion
- **Complete**: "3 documents processed. Ready for review." → Next button activates
- **Error**: Red banner "2 files failed to process. Remove or retry."
- **Duplicate**: Yellow banner "Document already exists in this session."

### File Requirements Display
- ✅ PDF, PNG, JPG, TIFF
- ✅ Up to 20MB per file
- ✅ Up to 20 files per batch
- Key information shown as subtle badges, not wall of text

---

## Step 3 — Review Items

**When**: Documents processed and classified

| Element | Description |
|---|---|
| **Step indicator** | "Step 3 of 4 — Review Items" |
| **Summary bar** | "5 items — 3 income, 2 deductions — 1 needs review" |
| **Item cards** | One card per item (not a table) |

### Item Card Design

```
┌────────────────────────────────────────────────────────────────────┐
│ [Income] [High confidence] [Needs review]                         │
│                                                                    │
│  $1,200.00                                                        │
│  Salary — Main employer                                           │
│  Reference: D1 — Salary, wages, allowances                        │
│                                                                    │
│  Risk: Low  |  Evidence: Complete  |  Source: payslip-jan.pdf     │
│                                                                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │ ✅ Confirm│  │ ❌ Exclude│  │ 🏷️ Edit  │  │ 🔍 View  │          │
│  │          │  │          │  │ Amount   │  │ Source  │           │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘          │
└────────────────────────────────────────────────────────────────────┘
```

### Actions per item
- **Confirm**: Mark as `user_confirmed` — green check, item moves to confirmed list
- **Exclude**: Mark as `excluded_by_user` — item hidden from export
- **Edit**: Inline amount/description edit (existing feature, improved UX)
- **View Source**: Open OCR preview modal with highlighted match text

### Filter Bar
| Filter | Description |
|---|---|
| All items | Default view |
| Income only | `item_type = income` |
| Deductions only | `item_type = deduction` |
| Needs review | `review_status = needs_user_review` |
| Confirmed | `review_status = user_confirmed` |
| Excluded | `review_status = excluded_by_user` |

### Review Progress
```
Income:  [████████░░]  3 of 5 confirmed
Deductions: [██░░░░░░]  1 of 4 confirmed
Needs review: [▓▓▓▓░░░░]  2 of 3 reviewed
```

### States
- **No items**: "No items found. Upload documents to get started." (redirects to Step 2)
- **All confirmed**: Green banner "✓ All items reviewed. Ready for export."
- **Some flagged**: "2 items still need your review"
- **Export blocked**: "Cannot export — 3 items still need review"

---

## Step 4 — Export

**When**: All items reviewed (or user bypasses)

| Element | Description |
|---|---|
| **Step indicator** | "Step 4 of 4 — Export Review Pack" |
| **Summary** | Total income, total deductions, item counts, document count |
| **Export password** | "Set a password for your export pack" → input field |
| **Format selector** | "Encrypted ZIP (recommended)" / "Plain JSON" / "CSV only" |
| **Include option** | "Include source documents" checkbox |
| **Export button** | "Generate & Download" |
| **History** | Previous exports for this session (date, format, status) |

### Export Confirmation
```
┌────────────────────────────────────────────────────────────────────┐
│  📦 Export Complete                                                │
│                                                                    │
│  • 3 income items ($4,200.00)                                     │
│  • 4 deduction items ($890.50)                                    │
│  • 5 source documents                                             │
│  • Password-protected with AES-256 encryption                     │
│                                                                    │
│  [📥 Download Export Pack]  [📋 Copy Summary]  [🔄 Export Again]│
│                                                                    │
│  Your export data is not stored on this server after download.     │
└────────────────────────────────────────────────────────────────────┘
```

### States
- **Ready**: Green banner "All 7 items reviewed and confirmed"
- **Unreviewed**: Yellow warning "3 items still need review — export anyway?"
- **No export password**: Button disabled until password entered
- **Exporting**: Progress spinner "Encrypting and packaging..."
- **Complete**: Download link + summary card
- **History**: Previous exports listed with timestamps and formats

---

## Archive / Session Management

### From Home (Step 1)
| Action | UX |
|---|---|
| **Rename** | Click ✏️ icon → inline edit → Enter to save (existing) |
| **Archive** | Click 📦 icon → moves to archived (collapsible section) |
| **Delete** | Click 🗑️ icon → confirmation dialog "Delete all data?" (existing) |

### From Session Page
| Action | UX |
|---|---|
| **Back** | ← Back to sessions (existing) |
| **Archive** | Button in header (existing) |
| **Delete** | Button with confirmation (existing) |
| **Export** | Button that navigates to Step 4 |

---

## Document Lifecycle (User-Facing)

The following statuses are shown to the user. Internal states are hidden.

| User Sees | Internal Status | Meaning |
|---|---|---|
| **Queued** | `uploaded` | Waiting for processing |
| **Extracting text** | `extracting_text` | OCR in progress |
| **Classifying** | `classifying` | AI/rules processing |
| **Ready** | `classified` | Done — items available for review |
| **Review needed** | `needs_review` | Low confidence or detected issue |
| **Reviewed** | `reviewed` | User has seen and actioned items |
| **Duplicate** | `duplicate_detected` | Same content already uploaded |
| **Failed** | `classification_failed` | Error during processing — retry available |
| **Included in export** | `included_in_report` | Document packed in export |
| **Archived** | `archived` | User archived this session |

---

## Visual Design Language

```
Colors:
  Background: white, gray-50
  Primary: blue-600 (#2563eb) — trustworthy, calm
  Success: green-600 (#16a34a) — confirming/exports
  Warning: amber-500 (#f59e0b) — review needed
  Error: red-600 (#dc2626) — failures/errors
  Text: gray-900, gray-500
  Links: blue-600 with underline

Typography:
  Headings: 16px-20px semibold
  Body: 14px regular
  Labels: 12px medium
  Monospace: for item amounts

Spacing:
  Cards: p-4, rounded-lg, border-gray-200
  Sections: space-y-6
  Grid: gap-3

Icons:
  Actionable icons with text labels (not icon-only)
  Status dots: ● green, ● yellow, ● red, ● gray
  Step numbers: ① ② ③ ④ with active/completed states

Emotions to evoke:
  "This is safe" → lock icons, encryption badges, local-only indicators
  "This is guided" → step numbers, progress bars, clear next actions
  "This is professional" → clean cards, no debug/sysadmin info, proper spacing
  "This is for me" → session titles, financial years, personal summary
```

---

## Error States & Empty States

| Page | Empty State | Error State |
|---|---|---|
| **Unlock** | First-time setup wizard | "Incorrect password, X attempts remaining" |
| **Select Tax Year** | "No sessions yet. Start by selecting a tax year." | "Could not load sessions. [Retry]" |
| **Upload Documents** | Large drag-drop zone with instructions | "Upload failed. 2 of 5 files errored. [Retry failed]" |
| **Review Items** | "No items to review. Upload documents first." | "Could not load items. [Retry]" |
| **Export** | "Review items first before exporting." | "Export failed. [Try Again]" |
| **404** | Centered "Page not found" with back link | Already implemented |

---

## Mobile Responsiveness

- Each step works on mobile (single column, touch-friendly buttons)
- Drag-drop zone falls back to file picker tap
- Review cards stack vertically
- Export button full-width on mobile
- Step indicator collapses to dots on small screens

---

## Comparison: v1 vs v2 UX

| Aspect | v1 (Current) | v2 (Target) |
|---|---|---|
| **First impression** | Login to nothing useful | Unlock screen + setup wizard |
| **Navigation** | 5 confusing tabs | 4 clear steps with progress |
| **Documents** | Collapsed at bottom | Prominent in Step 2 |
| **Review** | Table with Approve/Delete | Cards with Confirm/Exclude/Edit/View |
| **Export** | Tab with JSON/CSV | Step with encryption + password |
| **Feedback** | Minimal | Review progress, export confirmation |
| **Security perception** | None | Lock icons, encryption badges, local-only indicators |
| **Empty states** | "No sessions yet" | Guidance throughout |
| **Error handling** | Red text | Clear messages with actionable retries |
| **Mobile** | Poor | Responsive |

---

## Implementation Notes

- **Phase 1 delivers**: All 4 steps with working navigation, item cards, review progress
- **Phase 2 adds**: Unlock screen, first-time setup
- **Phase 3 adds**: Document lifecycle badges in Step 2
- **Phase 5 adds**: New review actions (Exclude, Flag for Agent)
- **Phase 6 adds**: Encrypted export prompt + format selector
- No existing component needs to be deleted — new `WorkflowStepper` routes to new pages, old session page remains accessible via direct link
