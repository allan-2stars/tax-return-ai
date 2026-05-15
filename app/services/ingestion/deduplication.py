"""
Deduplication service.
Two checks run on every upload — both required. See CLAUDE.md deduplication rules.
"""
import hashlib


def compute_file_hash(data: bytes) -> str:
    """SHA-256 hex digest. Store in documents.file_hash."""
    return hashlib.sha256(data).hexdigest()


async def check_hash_duplicate(file_hash: str, session_id: str, repo) -> object | None:
    """Return existing Document if same hash exists in this session."""
    return await repo.find_by_hash(session_id=session_id, file_hash=file_hash)


async def check_content_duplicate(
    supplier: str | None,
    amount: float | None,
    date: str | None,
    session_id: str,
    repo,
) -> object | None:
    """
    Return existing TaxItem if supplier + amount + date all match in same session.
    Skipped (returns None) if any of the three values is None.
    """
    if not all([supplier, amount, date]):
        return None
    return await repo.find_duplicate(
        session_id=session_id, supplier=supplier, amount=amount, date=date
    )
