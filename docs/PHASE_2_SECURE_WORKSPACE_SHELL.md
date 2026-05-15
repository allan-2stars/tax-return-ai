# Phase 2 Secure Workspace Shell — Implementation Notes

## Scope implemented in this phase
- Added frontend app state model for secure-workspace shell states:
  - `UNINITIALIZED`
  - `LOCKED`
  - `UNLOCKING`
  - `UNLOCKED`
  - `SESSION_EXPIRED`
- Implemented placeholder auth shell screens:
  - Create Master Password
  - Show Recovery Key
  - Confirm Recovery Key
  - Unlock Workspace
  - Session Expired
- Added protected app shell after unlock:
  - Left sidebar navigation: Dashboard, Documents, Review Items, Issues, Review Pack, Settings
  - Top context bar with Tax Year selector
  - Central workspace content area
  - Right-side privacy trust panel
- Added guided dashboard workflow cards:
  - Step 1 Add documents
  - Step 2 Review extracted items
  - Step 3 Resolve issues
  - Step 4 Generate review pack
- Preserved existing functionality reachability by linking from new shell to existing session pages.

## What is mock/placeholder
- Auth/session logic is temporary frontend-only placeholder in `frontend/lib/mockAuth.ts`.
- Tax year workspace selector currently uses isolated mock data in `frontend/lib/mockWorkspaces.ts`.
- Placeholder logic is intentionally isolated and marked with TODO comments for backend-auth replacement.

## What security is not implemented yet
- No backend-authenticated login/session verification yet.
- No secure password hashing on backend yet.
- No encrypted storage at rest yet.
- No encrypted export implementation yet.
- No production-grade recovery-key verification flow yet.

## Explicit non-claims
- This phase does not claim secure authentication is complete.
- This phase does not claim document encryption is implemented.
- This phase does not change OCR or AI provider pipelines.
- This phase does not modify Docker Compose ports/topology.

## Next phase recommendation
1. Implement backend user/auth session models and APIs.
2. Replace mock auth state with backend session checks and lock timeout policy.
3. Introduce real workspace model/API and bind tax-year selector to backend data.
4. Add route-level protection middleware and end-to-end auth tests.
5. Keep OCR/AI/classification logic unchanged until auth/workspace foundation is stable.
