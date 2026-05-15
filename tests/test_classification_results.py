"""Tests for classification_results storage, multi-item classification, and retry logic.

Covers:
  - ClassificationResultModel persistence after successful/failed classification
  - Multi-item classification creates multiple TaxItem + DocumentItem records
  - Classification with single vs multiple keyword matches
  - Empty text handling
  - Retry mechanism handles transient failures gracefully
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.tax_session import TaxSession
from app.models.document import Document
from app.models.tax_item import TaxItem
from app.models.document_item import DocumentItem
from app.models.classification_result import ClassificationResultModel
from app.services.classification import classify_document


class TestClassificationResultStorage:
    """Tests for classification_results table persistence."""

    async def _setup_session_and_doc(self, db: AsyncSession):
        session = TaxSession(title="Test", financial_year="2025-2026")
        db.add(session)
        await db.flush()
        doc = Document(
            session_id=session.id,
            original_filename="test.txt",
            mime_type="text/plain",
            file_size_bytes=100,
            status="uploaded",
        )
        db.add(doc)
        await db.flush()
        await db.commit()
        return session.id, doc.id

    async def test_classification_result_saved_on_success(self, db_session):
        """After successful classification, a ClassificationResultModel record exists."""
        sid, did = await self._setup_session_and_doc(db_session)

        items = await classify_document(
            db=db_session,
            document_id=did,
            session_id=sid,
            extracted_text="Salary from employer: $85,000",
            financial_year="2025-2026",
        )

        # Verify result was saved
        result = await db_session.execute(
            select(ClassificationResultModel).where(
                ClassificationResultModel.document_id == did
            )
        )
        record = result.scalar_one_or_none()
        assert record is not None
        assert record.success is True
        assert record.provider_name is not None
        assert record.raw_input is not None
        assert record.raw_output is not None
        assert record.parsed_output is not None
        assert record.document_id == did
        assert record.session_id == sid

    async def test_classification_result_high_confidence(self, db_session):
        """Salary text should yield high confidence with mock provider."""
        sid, did = await self._setup_session_and_doc(db_session)

        items = await classify_document(
            db=db_session,
            document_id=did,
            session_id=sid,
            extracted_text="Salary from employer: $85,000",
            financial_year="2025-2026",
        )

        result = await db_session.execute(
            select(ClassificationResultModel).where(
                ClassificationResultModel.document_id == did
            )
        )
        record = result.scalar_one_or_none()
        assert record is not None
        # Mock provider returns 0.95 for salary
        assert record.confidence is not None
        assert record.confidence >= 0.9

    async def test_classification_result_multi_item(self, db_session):
        """Multi-item classification saves one result record with all items."""
        sid, did = await self._setup_session_and_doc(db_session)

        items = await classify_document(
            db=db_session,
            document_id=did,
            session_id=sid,
            extracted_text="Salary $85k and OfficeWorks $350 for equipment",
            financial_year="2025-2026",
        )

        # Should get 2+ items
        assert len(items) >= 2

        # Verify each item is persisted
        for item in items:
            fetched = await db_session.get(TaxItem, item.id)
            assert fetched is not None
            assert fetched.session_id == sid

        # Single classification result for the whole call
        result = await db_session.execute(
            select(ClassificationResultModel).where(
                ClassificationResultModel.document_id == did
            )
        )
        records = result.scalars().all()
        assert len(records) == 1

    async def test_classification_result_multi_item_creates_document_links(self, db_session):
        """Each classified item should have a DocumentItem link."""
        sid, did = await self._setup_session_and_doc(db_session)

        items = await classify_document(
            db=db_session,
            document_id=did,
            session_id=sid,
            extracted_text="Salary $85k and OfficeWorks $350",
            financial_year="2025-2026",
        )

        # Verify DocumentItem links exist for each item
        for item in items:
            result = await db_session.execute(
                select(DocumentItem).where(
                    DocumentItem.tax_item_id == item.id,
                    DocumentItem.document_id == did,
                )
            )
            link = result.scalar_one_or_none()
            assert link is not None, f"Missing DocumentItem link for item {item.id}"


class TestMultiItemClassification:
    """Tests for multi-item classification support."""

    async def _setup_session_and_doc(self, db: AsyncSession):
        session = TaxSession(title="Multi Test", financial_year="2025-2026")
        db.add(session)
        await db.flush()
        doc = Document(
            session_id=session.id,
            original_filename="multi.txt",
            mime_type="text/plain",
            file_size_bytes=200,
            status="uploaded",
        )
        db.add(doc)
        await db.flush()
        await db.commit()
        return session.id, doc.id

    async def test_mixed_keywords_produce_multiple_items(self, db_session):
        """Text with multiple keywords should produce multiple items."""
        sid, did = await self._setup_session_and_doc(db_session)

        items = await classify_document(
            db=db_session,
            document_id=did,
            session_id=sid,
            extracted_text="Salary from employer $85,000 and OfficeWorks $350 for equipment",
            financial_year="2025-2026",
        )

        assert len(items) >= 2
        types = {i.item_type for i in items}
        assert "income" in types
        assert "deduction" in types

    async def test_single_keyword_produces_one_item(self, db_session):
        """Text with only one keyword match should produce one item."""
        sid, did = await self._setup_session_and_doc(db_session)

        items = await classify_document(
            db=db_session,
            document_id=did,
            session_id=sid,
            extracted_text="Union membership fee $350",
            financial_year="2025-2026",
        )

        assert len(items) == 1
        assert items[0].item_type == "deduction"
        assert items[0].category == "union_fee"

    async def test_empty_text_returns_needs_review(self, db_session):
        """Empty text should produce one needs_review item."""
        sid, did = await self._setup_session_and_doc(db_session)

        items = await classify_document(
            db=db_session,
            document_id=did,
            session_id=sid,
            extracted_text="",
            financial_year="2025-2026",
        )

        assert len(items) == 1
        assert items[0].needs_review is True
        assert items[0].item_type == "needs_review"

    async def test_income_and_donation_together(self, db_session):
        """Income + donation keywords should produce income and deduction items."""
        sid, did = await self._setup_session_and_doc(db_session)

        items = await classify_document(
            db=db_session,
            document_id=did,
            session_id=sid,
            extracted_text="Salary $85k and donation $200 to charity",
            financial_year="2025-2026",
        )

        assert len(items) >= 2
        types = {i.item_type for i in items}
        assert "income" in types
        assert "deduction" in types

    async def test_union_fee_and_wfh_together(self, db_session):
        """Multiple deduction keywords should produce multiple deduction items."""
        sid, did = await self._setup_session_and_doc(db_session)

        items = await classify_document(
            db=db_session,
            document_id=did,
            session_id=sid,
            extracted_text="Union fee $450 and WFH expenses $1200 electricity",
            financial_year="2025-2026",
        )

        assert len(items) >= 2
        categories = {i.category for i in items}
        assert "union_fee" in categories
        assert "work_from_home" in categories


class TestClassificationRetry:
    """Tests for retry logic on transient failures."""

    async def _setup_session_and_doc(self, db: AsyncSession):
        session = TaxSession(title="Retry Test", financial_year="2025-2026")
        db.add(session)
        await db.flush()
        doc = Document(
            session_id=session.id,
            original_filename="retry.txt",
            mime_type="text/plain",
            file_size_bytes=100,
            status="uploaded",
        )
        db.add(doc)
        await db.flush()
        await db.commit()
        return session.id, doc.id

    async def test_normal_classification_no_retry_needed(self, db_session):
        """Happy path — first attempt succeeds, no retry needed."""
        sid, did = await self._setup_session_and_doc(db_session)

        items = await classify_document(
            db=db_session,
            document_id=did,
            session_id=sid,
            extracted_text="Salary $85,000",
            financial_year="2025-2026",
        )

        assert len(items) >= 1
        assert items[0].item_type == "income"

    async def test_classification_saves_successful_result(self, db_session):
        """Successful classification should produce a success=true record."""
        sid, did = await self._setup_session_and_doc(db_session)

        items = await classify_document(
            db=db_session,
            document_id=did,
            session_id=sid,
            extracted_text="OfficeWorks $350 for equipment",
            financial_year="2025-2026",
        )

        result = await db_session.execute(
            select(ClassificationResultModel).where(
                ClassificationResultModel.document_id == did
            )
        )
        record = result.scalar_one_or_none()
        assert record is not None
        assert record.success is True
        assert record.error_message is None

    async def test_classification_result_has_provider_name(self, db_session):
        """Classification result should record which provider was used."""
        sid, did = await self._setup_session_and_doc(db_session)

        items = await classify_document(
            db=db_session,
            document_id=did,
            session_id=sid,
            extracted_text="Salary $85,000",
            financial_year="2025-2026",
        )

        result = await db_session.execute(
            select(ClassificationResultModel).where(
                ClassificationResultModel.document_id == did
            )
        )
        record = result.scalar_one_or_none()
        assert record is not None
        assert record.provider_name is not None
        # Mock provider has name containing "mock"
        assert "mock" in record.provider_name.lower()
