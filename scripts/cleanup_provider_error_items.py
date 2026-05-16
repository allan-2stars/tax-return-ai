"""Cleanup legacy provider-error tax items.

Detects obvious provider error rows that were historically written as tax items
and marks them excluded with a system note. This avoids deleting potentially
useful user-reviewed data.

Usage:
  ./.venv/bin/python scripts/cleanup_provider_error_items.py --dry-run
  ./.venv/bin/python scripts/cleanup_provider_error_items.py --apply
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.tax_item import TaxItem

ERROR_PATTERNS = [
    "anthropic api error",
    "openai api error",
    "could not resolve authentication method",
    "invalid_api_key",
    "api call failed:",
]


def _matches_provider_error(item: TaxItem) -> bool:
    text_fields = [item.description or "", item.review_reason or ""]
    joined = " ".join(text_fields).lower()
    return any(pattern in joined for pattern in ERROR_PATTERNS)


async def _run_cleanup(db, apply: bool) -> dict[str, int]:
    changed = 0
    scanned = 0
    result = await db.execute(select(TaxItem))
    items = result.scalars().all()
    for item in items:
        scanned += 1
        if not _matches_provider_error(item):
            continue
        changed += 1
        if not apply:
            continue
        item.review_status = "excluded"
        item.needs_review = False
        item.review_reason = "System cleanup: legacy provider error row excluded."
        item.reviewed_by = "system"
        item.reviewed_at = datetime.now(timezone.utc)
    if apply:
        await db.commit()
    return {"scanned": scanned, "matched": changed}


async def cleanup_provider_error_items(apply: bool, db=None) -> dict[str, int]:
    if db is not None:
        return await _run_cleanup(db, apply=apply)
    async with async_session_factory() as session:
        return await _run_cleanup(session, apply=apply)


async def _main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    result = await cleanup_provider_error_items(apply=args.apply)
    print(result)


if __name__ == "__main__":
    asyncio.run(_main())
