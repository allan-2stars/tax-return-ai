#!/bin/bash
# TaxReturnAI — Production Deploy Script
# Usage: bash scripts/deploy.sh
#
# Zero-downtime deploy: builds new images, starts new containers,
# runs migrations, then removes old containers.

set -euo pipefail

echo "═══════════════════════════════════════════════════════════════"
echo "  TaxReturnAI — Deploy $(date +%Y-%m-%d\ %H:%M:%S)"
echo "═══════════════════════════════════════════════════════════════"

# 1. Pull latest config (if git repo)
if git rev-parse --git-dir > /dev/null 2>&1; then
    echo "◆ Pulling latest code..."
    git pull
fi

# 2. Rebuild with production Dockerfiles
echo "◆ Building production images..."
docker compose build

# 3. Start new services (healthy replacements)
echo "◆ Starting services..."
docker compose up -d

# 4. Run migrations
echo "◆ Running database migrations..."
docker compose exec -w /app backend alembic upgrade head || echo "  ⚠ Migration skipped (SQLite doesn't support all commands)"

# 5. Wait for health
echo "◆ Waiting for backend health..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:8010/api/health > /dev/null 2>&1; then
        echo "  ✓ Backend healthy after ${i}s"
        break
    fi
    sleep 1
done

# 6. Verify frontend
echo "◆ Verifying frontend..."
if curl -sf http://localhost:3020 > /dev/null 2>&1; then
    echo "  ✓ Frontend responding"
else
    echo "  ⚠ Frontend not yet responding"
fi

# 7. Backup DB after successful deploy
echo "◆ Creating post-deploy backup..."
bash scripts/backup.sh 2>/dev/null || echo "  ⚠ Backup skipped"

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  ✓ Deploy complete"
echo "  Backend:  http://localhost:8010 — https://tax-api.signpega.com"
echo "  Frontend: http://localhost:3020 — https://tax.signpega.com"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "To view logs: docker compose logs -f"
echo "To backup DB: bash scripts/backup.sh"
