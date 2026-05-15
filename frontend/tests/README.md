# Frontend Tests

## Setup

```bash
# Install test dependencies
npm install --save-dev vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom

# Or via Docker
cd .. && docker compose exec frontend npm install --save-dev vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom
```

## Run

```bash
npm test              # single run
npm run test:watch    # watch mode
```

## What's Tested

| Test File | Coverage |
|---|---|
| `DisclaimerBanner.test.tsx` | Renders disclaimer text, ARIA role |
| `SessionCard.test.tsx` | Renders title/notes/FY/status, fires onSelect |
| `DocumentUploader.test.tsx` | Renders form elements, submit flow (needs vitest + jsdom) |
| `ReviewList.test.tsx` | Empty state, item list, approve/flag/delete actions |
| `ExportButton.test.tsx` | Render, fetch call on click, error handling |
