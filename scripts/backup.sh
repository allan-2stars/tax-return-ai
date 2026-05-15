#!/bin/bash
# DB backup script — runs as a cron job inside the container or host
# Usage: bash scripts/backup.sh

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./data/backups}"
DB_PATH="${DB_PATH:-./data/taxapp.db}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
TIMESTAMP=$(date +"%Y%m%d-%H%M%S")

mkdir -p "$BACKUP_DIR"

# Check if we're using SQLite or PostgreSQL
if [ -f "$DB_PATH" ]; then
    # SQLite backup
    cp "$DB_PATH" "$BACKUP_DIR/taxapp-$TIMESTAMP.db"
    echo "Backed up SQLite: $BACKUP_DIR/taxapp-$TIMESTAMP.db ($(du -h "$BACKUP_DIR/taxapp-$TIMESTAMP.db" | cut -f1))"
elif command -v pg_dump &> /dev/null; then
    # PostgreSQL backup
    PGPASSWORD="${PGPASSWORD:-}" pg_dump \
        -h "${PGHOST:-localhost}" \
        -U "${PGUSER:-taxapp}" \
        -d "${PGDATABASE:-taxapp}" \
        -f "$BACKUP_DIR/taxapp-$TIMESTAMP.sql"
    echo "Backed up PostgreSQL: $BACKUP_DIR/taxapp-$TIMESTAMP.sql ($(du -h "$BACKUP_DIR/taxapp-$TIMESTAMP.sql" | cut -f1))"
else
    echo "No database found to back up."
    exit 1
fi

# Clean old backups
find "$BACKUP_DIR" -name "taxapp-*" -mtime +$RETENTION_DAYS -delete
echo "Cleaned backups older than $RETENTION_DAYS days"
