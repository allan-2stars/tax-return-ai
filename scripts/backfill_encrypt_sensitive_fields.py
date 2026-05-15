"""Backfill encrypted sensitive DB fields.

Usage:
  python scripts/backfill_encrypt_sensitive_fields.py --dry-run --confirm
  python scripts/backfill_encrypt_sensitive_fields.py --confirm
"""

from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.models.document_page import DocumentPage
from app.models.tax_item import TaxItem
from app.models.classification_result import ClassificationResultModel
from app.services.security.key_cache import get_user_active_key
from app.services.security.field_encryption import (
    encrypt_text,
    ENCRYPTION_VERSION,
    DEFAULT_KEY_VERSION,
)


async def backfill_sensitive_fields(db: AsyncSession, key: bytes, dry_run: bool) -> dict[str, int]:
    counts = {
        "document_pages_encrypted": 0,
        "tax_item_description_encrypted": 0,
        "tax_item_notes_encrypted": 0,
        "tax_item_review_reason_encrypted": 0,
        "classification_raw_input_encrypted": 0,
        "classification_raw_output_encrypted": 0,
    }
    page_rows = await db.execute(select(DocumentPage))
    for page in page_rows.scalars().all():
        if page.text and not page.text_enc:
            counts["document_pages_encrypted"] += 1
            if not dry_run:
                page.text_enc = encrypt_text(page.text, key)
                page.encryption_version = ENCRYPTION_VERSION
                page.key_version = DEFAULT_KEY_VERSION

    item_rows = await db.execute(select(TaxItem))
    for item in item_rows.scalars().all():
        if item.description and not item.description_enc:
            counts["tax_item_description_encrypted"] += 1
            if not dry_run:
                item.description_enc = encrypt_text(item.description, key)
                item.encryption_version = ENCRYPTION_VERSION
                item.key_version = DEFAULT_KEY_VERSION
        if getattr(item, "notes", None) and not getattr(item, "notes_enc", None):
            counts["tax_item_notes_encrypted"] += 1
            if not dry_run:
                item.notes_enc = encrypt_text(item.notes, key)
                item.encryption_version = ENCRYPTION_VERSION
                item.key_version = DEFAULT_KEY_VERSION
        if item.review_reason and not item.review_reason_enc:
            counts["tax_item_review_reason_encrypted"] += 1
            if not dry_run:
                item.review_reason_enc = encrypt_text(item.review_reason, key)
                item.encryption_version = ENCRYPTION_VERSION
                item.key_version = DEFAULT_KEY_VERSION

    cls_rows = await db.execute(select(ClassificationResultModel))
    for rec in cls_rows.scalars().all():
        if rec.raw_input and not rec.raw_input_enc:
            counts["classification_raw_input_encrypted"] += 1
            if not dry_run:
                rec.raw_input_enc = encrypt_text(rec.raw_input, key)
                rec.encryption_version = ENCRYPTION_VERSION
                rec.key_version = DEFAULT_KEY_VERSION
        if rec.raw_output and not rec.raw_output_enc:
            counts["classification_raw_output_encrypted"] += 1
            if not dry_run:
                rec.raw_output_enc = encrypt_text(rec.raw_output, key)
                rec.encryption_version = ENCRYPTION_VERSION
                rec.key_version = DEFAULT_KEY_VERSION

    if not dry_run:
        await db.commit()
    return counts


async def run_backfill(dry_run: bool) -> dict[str, int]:
    async with AsyncSessionLocal() as db:
        user_row = await db.execute(select(User).where(User.is_active == True))  # noqa: E712
        user = user_row.scalar_one_or_none()
        if not user:
            return {
                "document_pages_encrypted": 0,
                "tax_item_description_encrypted": 0,
                "tax_item_notes_encrypted": 0,
                "tax_item_review_reason_encrypted": 0,
                "classification_raw_input_encrypted": 0,
                "classification_raw_output_encrypted": 0,
            }
        key = get_user_active_key(user.id)
        if not key:
            raise RuntimeError("No unlocked workspace key in memory. Unlock first, then rerun.")
        return await backfill_sensitive_fields(db, key, dry_run=dry_run)


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill encryption for sensitive fields.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    if not args.confirm:
        raise SystemExit("Refusing to run without --confirm")
    counts = asyncio.run(run_backfill(dry_run=args.dry_run))
    for key, value in counts.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
