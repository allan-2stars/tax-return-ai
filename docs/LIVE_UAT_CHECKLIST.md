# Live UAT Checklist (Phase 16E)

Date: 2026-05-16  
Target environment: `https://taxai.signpega.com`  
API target: `https://taxai-api.signpega.com`  
Purpose: real human clickthrough validation + release-candidate bugfix tracking

## Instructions

- Perform each step in order as a normal user.
- Capture a screenshot (or short reference note) for each step.
- Record observed issues immediately.
- Only apply fixes for issues reproduced in live UAT.

Result values:
- `PASS`
- `FAIL`
- `BLOCKED`
- `N/A`

Fix status values:
- `Not Needed`
- `Open`
- `In Progress`
- `Fixed`
- `Deferred`

## 15-Step Walkthrough

| # | Step | Result | Screenshot / Reference | Observed Issue | Fix Status |
|---|---|---|---|---|---|
| 1 | First-time setup | PENDING |  |  | Not Needed |
| 2 | Recovery key display/save | PENDING |  |  | Not Needed |
| 3 | Unlock | PENDING |  |  | Not Needed |
| 4 | Create/select FY2025 workspace | PENDING |  |  | Not Needed |
| 5 | Upload valid PDF | PENDING |  |  | Not Needed |
| 6 | Upload unsupported file | PENDING |  |  | Not Needed |
| 7 | View processing result | PENDING |  |  | Not Needed |
| 8 | Review extracted items | PENDING |  |  | Not Needed |
| 9 | Confirm/exclude/tax-agent-review items | PENDING |  |  | Not Needed |
| 10 | Generate encrypted review pack | PENDING |  |  | Not Needed |
| 11 | Download export | PENDING |  |  | Not Needed |
| 12 | Lock workspace | PENDING |  |  | Not Needed |
| 13 | Unlock again | PENDING |  |  | Not Needed |
| 14 | Forgot password/recovery reset | PENDING |  |  | Not Needed |
| 15 | Verify old sessions invalidated | PENDING |  |  | Not Needed |

## UAT Notes

- Tester:
- Browser/device:
- Test date/time:
- Build/commit:
- Environment notes:
- Network notes:

### Issues Log

| ID | Step # | Summary | Repro Notes | Severity | Status |
|---|---|---|---|---|---|
| UAT-001 |  |  |  |  |  |

## Release-Candidate Readiness Notes

- UAT completion status: `Pending live run`
- Blocking defects: `None recorded yet`
- Non-blocking defects: `None recorded yet`
- Recommendation after live UAT: `TBD`

## Pre-UAT Baseline (Automated Checks)

Executed before live run:

```bash
cd /home/pi/tax-return-ai/frontend && npm run test:workspace
cd /home/pi/tax-return-ai && ./.venv/bin/pytest -q tests/test_auth_workspace.py tests/test_upload_endpoint.py
```

Baseline result:
- Frontend workspace tests: PASS
- Focused backend auth/upload tests: PASS
