from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.export_package import ExportPackageModel


@dataclass
class ExportCleanupResult:
    deleted_file_count: int = 0
    skipped_missing_file_count: int = 0
    marked_deleted_count: int = 0


async def cleanup_deleted_review_packs(
    db: AsyncSession,
    older_than_days: int | None = None,
    include_ready_exports: bool = False,
) -> ExportCleanupResult:
    """Cleanup stale encrypted export files.

    Default behavior:
    - cleans DB records already marked deleted
    - removes orphan files if present, no-op when already gone
    - never touches active ready exports
    """
    result = ExportCleanupResult()

    deleted_rows = await db.execute(
        select(ExportPackageModel).where(ExportPackageModel.status == "deleted")
    )
    for record in deleted_rows.scalars().all():
        if not record.storage_path:
            result.skipped_missing_file_count += 1
            continue
        path = Path(record.storage_path)
        if path.exists() and path.is_file():
            path.unlink()
            result.deleted_file_count += 1
        else:
            result.skipped_missing_file_count += 1
        record.storage_path = None

    if older_than_days is not None and older_than_days >= 0:
        cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
        old_rows = await db.execute(
            select(ExportPackageModel).where(
                ExportPackageModel.created_at <= cutoff,
                ExportPackageModel.storage_path.is_not(None),
                ExportPackageModel.status != "deleted",
            )
        )
        for record in old_rows.scalars().all():
            if record.status == "ready" and not include_ready_exports:
                continue
            path = Path(record.storage_path or "")
            if path.exists() and path.is_file():
                path.unlink()
                result.deleted_file_count += 1
            record.storage_path = None
            record.status = "deleted"
            result.marked_deleted_count += 1

    await db.flush()
    return result

