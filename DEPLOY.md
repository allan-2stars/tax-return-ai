# Deploy to Production

## Quick Start (Raspberry Pi / Docker host)

```bash
# 1. Copy the package to the Pi
scp /tmp/tax-return-ai-deploy.tar.gz pi@<YOUR_PI_IP>:/home/pi/

# 2. SSH into the Pi
ssh pi@<YOUR_PI_IP>

# 3. Extract (overwrites existing project)
cd /home/pi/tax-return-ai  # or wherever the project lives
tar xzf ~/tax-return-ai-deploy.tar.gz .

# 4. Deploy
bash scripts/deploy.sh
```

## What's in This Deploy

### Bug Fixes
1. **Duplicate upload crash** — `_check_hash_duplicate` now uses `.scalars().first()` instead of `.scalar_one_or_none()` which threw `MultipleResultsFound`
2. **3s refresh loop** — removed auto-refresh `useEffect` from session page (JobStatusBanner handles polling instead)
3. **Accessibility warnings** — added `name` attributes to all form `<input>` and `<select>` elements

### New Features
4. **Home page stats** — Each session card shows document count, classified count, income/deduction/needs-review counts
5. **Upload success banner** — Green "Upload complete — document classified" banner with Dismiss button; red error banner on failure

### Files Changed
```
Modified:
  app/services/ingestion/pipeline.py          — dedup fix (.scalars().first())
  app/services/job/__init__.py                — get_job_status fields, re-raise fix
  app/routers/documents.py                    — pipeline commit flow
  app/routers/sessions.py                     — added GET /:id/stats endpoint
  frontend/app/session/[id]/page.tsx          — removed auto-refresh, uses JobStatusBanner
  frontend/components/DocumentUploader.tsx     — name attributes, direct fetch
  frontend/components/JobStatusBanner.tsx      — success/error banners with dismiss
  frontend/components/SessionCard.tsx          — stats display
  frontend/app/page.tsx                        — fetches stats per session
  frontend/lib/api.ts                          — SessionStats type, getSessionStats

Added:
  scripts/deploy.sh                           — one-command deploy script
  DEPLOY.md                                   — this file
```

## Verify After Deploy

1. **Upload a PDF** → should see progress bar (queued → running → succeeded)
2. **Upload the same file again** → should show "duplicate_detected" status
3. **Home page** → session cards should show document/item counts
4. **Session page** → should NOT auto-refresh every 3s (check Network tab in DevTools)
5. **Console** → no "form field element should have an id or name attribute" warnings
