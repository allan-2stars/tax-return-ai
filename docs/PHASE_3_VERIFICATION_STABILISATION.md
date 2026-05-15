# Phase 3 Verification Stabilisation

## Scope
Stabilise verification only for Phase 3 auth/workspace work:
- backend pytest execution path
- frontend lint non-interactive setup
- frontend WorkspaceApp focused tests

No new product features were added.
No Docker port changes were made.
No OCR/AI/classification pipeline changes were made.

## Fixes applied

### 1) Backend pytest path/config
- Updated `pyproject.toml` pytest config with:
  - `pythonpath = ["."]`
- Goal: avoid one-off `PYTHONPATH=...` shell exports.

### 2) Backend test runtime fixture stabilisation
- Root cause was twofold:
  - async SQLite (`aiosqlite`) connection path in this Pi runtime (Python 3.13 environment) hung before first auth test request completed.
  - test transport/config assumptions were mismatched with installed `httpx` API.
- Updated `tests/conftest.py` to use a deterministic focused harness:
  - minimal FastAPI app containing only `auth` + `workspaces` routers for these tests.
  - sync SQLite in-memory engine with `StaticPool` for deterministic, fast test isolation.
  - lightweight async adapter over sync SQLAlchemy session so existing async route/service signatures stay unchanged.
  - deterministic create/drop schema per test fixture lifecycle and explicit session close.

### 3) Frontend lint setup (non-interactive)
- Added `frontend/.eslintrc.json` with minimal Next config:
  - `{"extends": ["next/core-web-vitals"]}`
- This removes interactive `next lint` bootstrap prompt.

### 4) Frontend WorkspaceApp focused test fixes
- Fixed `vi.mock` hoist issue in `frontend/tests/WorkspaceApp.test.tsx` by mocking inline and using `vi.mocked(api)`.
- Added focused script in `frontend/package.json`:
  - `test:workspace` -> `vitest run tests/WorkspaceApp.test.tsx`
- Added `React` import compatibility where required by current test runtime.

## Commands run and results

### Required final checks
1. `docker compose config`
- Result: **PASS**

2. Backend focused auth/workspace tests
- Command: `./.venv/bin/pytest -q tests/test_auth_workspace.py`
- Result: **PASS** (`7 passed`)

3. `frontend` lint
- Command: `npm run lint`
- Result: **PASS** (`No ESLint warnings or errors`)

4. Frontend focused WorkspaceApp tests
- Command: `npm run test:workspace`
- Result: **PASS** (`5 passed`)

## What was fixed additionally
- Updated `app/services/auth/service.py` to normalize potentially naive DB datetimes before UTC comparison in session-expiry checks.
- Added focused backend command in `Makefile`:
  - `make test-auth` -> `./.venv/bin/pytest -q tests/test_auth_workspace.py`

## Regression classification
- Frontend lint/test issues addressed here were Phase 3 verification blockers and are fixed.
- Backend hang was test-infrastructure/runtime related, not a product-feature change.
- The datetime normalization change is a robustness fix surfaced by tests and relevant to SQLite-backed environments.

## Exact next recommendation
1. Keep `make test-auth` as the required focused gate for Phase 3 auth/workspace verification.
2. When broad backend suite is run, classify any failures separately as pre-existing vs Phase 3 regressions.
3. Optionally align runtime with project baseline Python (3.11) to reduce cross-version sqlite/async variance in future tests.

## Files changed in this stabilisation
- `pyproject.toml`
- `tests/conftest.py`
- `app/services/auth/service.py`
- `frontend/.eslintrc.json`
- `frontend/package.json`
- `frontend/tests/WorkspaceApp.test.tsx`
- `frontend/components/workspace/WorkspaceApp.tsx`
- `Makefile`
