"""Cleanup command for encrypted review-pack files."""
import argparse
import asyncio

from app.db.session import SessionLocal
from app.services.export.cleanup import cleanup_deleted_review_packs


async def _run(older_than_days: int | None, include_ready_exports: bool) -> None:
    async with SessionLocal() as db:
        result = await cleanup_deleted_review_packs(
            db,
            older_than_days=older_than_days,
            include_ready_exports=include_ready_exports,
        )
        await db.commit()
        print(
            f"deleted_file_count={result.deleted_file_count} "
            f"skipped_missing_file_count={result.skipped_missing_file_count} "
            f"marked_deleted_count={result.marked_deleted_count}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Cleanup encrypted review-pack files.")
    parser.add_argument("--older-than-days", type=int, default=None)
    parser.add_argument("--include-ready-exports", action="store_true")
    args = parser.parse_args()
    asyncio.run(_run(args.older_than_days, args.include_ready_exports))


if __name__ == "__main__":
    main()

