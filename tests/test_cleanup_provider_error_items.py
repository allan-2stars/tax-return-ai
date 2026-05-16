from sqlalchemy import select

from app.models.tax_item import TaxItem
from app.models.tax_session import TaxSession
from scripts.cleanup_provider_error_items import cleanup_provider_error_items


async def test_provider_error_cleanup_excludes_bad_rows(db_session):
    session = TaxSession(title="cleanup", financial_year="2025-2026", status="draft")
    db_session.add(session)
    await db_session.flush()

    bad = TaxItem(
        session_id=session.id,
        item_type="needs_review",
        category="needs_review",
        amount=None,
        description='Anthropic API error: Could not resolve authentication method',
        needs_review=True,
        review_status="needs_review",
    )
    good = TaxItem(
        session_id=session.id,
        item_type="deduction",
        category="tools_equipment",
        amount=25,
        description="Keyboard purchase",
        needs_review=True,
        review_status="needs_review",
    )
    db_session.add(bad)
    db_session.add(good)
    await db_session.commit()

    dry = await cleanup_provider_error_items(apply=False, db=db_session)
    assert dry["matched"] >= 1

    applied = await cleanup_provider_error_items(apply=True, db=db_session)
    assert applied["matched"] >= 1

    rows = await db_session.execute(select(TaxItem).where(TaxItem.id.in_([bad.id, good.id])))
    item_map = {i.id: i for i in rows.scalars().all()}
    assert item_map[bad.id].review_status == "excluded"
    assert item_map[bad.id].needs_review is False
    assert "legacy provider error row excluded" in (item_map[bad.id].review_reason or "").lower()
    assert item_map[good.id].review_status == "needs_review"
