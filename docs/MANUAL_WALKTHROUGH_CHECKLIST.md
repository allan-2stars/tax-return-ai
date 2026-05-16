# Manual Walkthrough Checklist (Phase 16D)

Date: 2026-05-16  
Project: `tax-return-ai`  
Scope: UX/runtime walkthrough verification and obvious bug pass (no architecture changes)

## Verification Method

- Backend/API verification via focused pytest suites.
- Frontend workflow verification via `WorkspaceApp` integration tests (`vitest`).
- Deployment sanity via `docker compose config`.
- This pass used test/runtime evidence in CLI environment; no full interactive browser recording was performed in this run.

## Checklist

| # | Step | Result | Evidence / Notes |
|---|---|---|---|
| 1 | first-time setup | PASS | Covered by auth setup tests in `tests/test_auth_workspace.py` (`setup-status`, first setup success). |
| 2 | recovery key display/save | PASS | Covered by frontend workflow tests (`WorkspaceApp` setup flow includes recovery key display/copy/download UI). |
| 3 | unlock | PASS | Covered by backend unlock success/failure tests and frontend locked/unlocked rendering tests. |
| 4 | create/select FY2025 workspace | PASS | Covered by backend workspace create/list tests + frontend tax-year selector tests. |
| 5 | upload valid PDF | PASS | Covered by `tests/test_upload_endpoint.py` and frontend upload tests (valid PDF success). |
| 6 | upload unsupported file | PASS | Covered by backend 415 structured error test and frontend unsupported-file messaging tests. |
| 7 | view processing result | PASS | Covered by frontend documents processing/status panel tests and outcome state rendering. |
| 8 | review extracted items | PASS | Covered by review list/filter rendering tests and empty-state guidance tests. |
| 9 | confirm/exclude/tax-agent-review items | PASS | Covered by item action/status transition tests in frontend/backend suites. |
| 10 | generate encrypted review pack | PASS | Covered by ready-state generate flow tests and backend encrypted pack route tests. |
| 11 | download export | PASS | Covered by backend download route tests and frontend export history/download UI tests. |
| 12 | lock workspace | PASS | Covered by frontend lock action and backend session/logout behavior tests. |
| 13 | unlock again | PASS | Covered by auth unlock + session-state tests. |
| 14 | forgot password/recovery reset | PASS | Covered by backend recovery reset tests and frontend recovery reset workflow tests. |
| 15 | verify old sessions invalidated | PASS | Covered by auth/session invalidation tests (logout/revoke behavior and reset invalidation expectations). |

## Commands Run

```bash
cd /home/pi/tax-return-ai/frontend && npm run test:workspace
cd /home/pi/tax-return-ai && ./.venv/bin/pytest -q tests/test_auth_workspace.py tests/test_upload_endpoint.py tests/test_workspace_scoped_routes.py
cd /home/pi/tax-return-ai && docker compose config
```

## Result Summary

- Overall walkthrough status: PASS (test-backed).
- Obvious UX/runtime bugs found in this pass: none new.
- No code changes were required for Phase 16D beyond this checklist document.

## Known Rough Edges (Already Tracked)

- Some walkthrough outcomes are test-backed rather than manually click-recorded in a live browser session.
- Issue engine remains a guided placeholder (not a full rule engine).
- Provider mode / retryable states are derived from current metadata and may be conservative for edge cases.
