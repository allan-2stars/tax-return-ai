"""Tests for the export service.

Covers:
  - generate_export: end-to-end package generation via DB
  - _generate_warnings: compliance warning generation (pure function)
  - Export shape matches frontend expectations
"""
from app.services.export import generate_export, _generate_warnings


class TestExportWarnings:
    """Pure function tests — no DB needed."""

    def _make_item(self, category="salary_wages", description="Test", amount=1000.0,
                   confidence=0.95, needs_review=False, item_type="income",
                   review_reason=None):
        """Helper to create a mock TaxItem-like object."""
        from types import SimpleNamespace
        return SimpleNamespace(
            id="item-1",
            item_type=item_type,
            category=category,
            amount=amount,
            description=description,
            confidence=confidence,
            needs_review=needs_review,
            review_reason=review_reason,
            ato_reference_hint=None,
        )

    def test_no_warnings_for_clean_items(self):
        warnings = _generate_warnings([
            self._make_item(category="salary_wages", needs_review=False),
            self._make_item(category="union_fee", needs_review=False),
        ])
        assert len(warnings) == 0

    def test_warning_for_needs_review_item(self):
        warnings = _generate_warnings([
            self._make_item(category="tools_equipment", needs_review=True),
        ])
        assert len(warnings) == 1
        assert "needs review" in warnings[0].lower()
        assert "D5" in warnings[0]

    def test_warning_for_low_confidence_auto_approved(self):
        warnings = _generate_warnings([
            self._make_item(confidence=0.5, needs_review=False),
        ])
        assert len(warnings) == 1
        assert "low confidence" in warnings[0].lower()

    def test_no_warning_low_confidence_needs_review(self):
        """Low confidence items that already need review aren't double-flagged."""
        warnings = _generate_warnings([
            self._make_item(confidence=0.5, needs_review=True, review_reason="Low confidence"),
        ])
        # Should only get the "needs review" warning, not the "low confidence but auto-approved" one
        needs_review_warnings = [w for w in warnings if "require human review" in w.lower()]
        assert len(needs_review_warnings) == 1

    def test_warning_for_no_amount_items(self):
        warnings = _generate_warnings([
            self._make_item(amount=None, item_type="deduction"),
            self._make_item(amount=None, item_type="income"),
            self._make_item(amount=None, item_type="out_of_scope"),
        ])
        no_amount = [w for w in warnings if "no dollar amount" in w.lower()]
        assert len(no_amount) == 1
        assert "2 item(s)" in no_amount[0]  # only income + deduction counts

    def test_warning_for_general_review_notice(self):
        warnings = _generate_warnings([
            self._make_item(category="tools_equipment", needs_review=True),
        ])
        review_notice = [w for w in warnings if "require human review" in w.lower()]
        assert len(review_notice) == 1

    def test_warnings_deduplicated(self):
        """Same item shouldn't generate duplicate warnings."""
        item = self._make_item(category="tools_equipment", needs_review=True)
        # Two calls with same item
        warnings = _generate_warnings([item, item])
        assert len(warnings) == 2  # D5 hint + general review notice


class TestExportService:
    """Integration tests requiring DB — checks the full generate_export flow."""

    async def _create_session(self, db):
        from app.models.tax_session import TaxSession
        s = TaxSession(title="Export Test", financial_year="2025-2026")
        db.add(s)
        await db.flush()
        return s.id

    async def test_generate_export_basic_shape(self, db_session):
        """Verify the export package matches the expected top-level shape."""
        sid = await self._create_session(db_session)

        pkg = await generate_export(db_session, sid)

        assert "export_metadata" in pkg
        assert "session" in pkg
        assert "summary" in pkg
        assert "income_items" in pkg
        assert "deduction_items" in pkg
        assert "needs_review_items" in pkg
        assert "out_of_scope_items" in pkg
        assert "source_documents" in pkg
        assert "export_warnings" in pkg

        # Verify metadata
        assert pkg["export_metadata"]["status"] == "draft"
        assert "disclaimer" in pkg["export_metadata"]
        assert "generated_at" in pkg["export_metadata"]

        # Verify session info
        assert pkg["session"]["id"] == sid
        assert pkg["session"]["financial_year"] == "2025-2026"

        # Empty session should have zero counts
        assert pkg["summary"]["total_documents"] == 0
        assert pkg["summary"]["total_items"] == 0

    async def test_generate_export_with_documents(self, db_session):
        """Documents should appear in source_documents."""
        from app.models.document import Document

        sid = await self._create_session(db_session)
        doc = Document(
            session_id=sid, original_filename="test.pdf",
            mime_type="application/pdf", file_size_bytes=1234,
            status="processed",
        )
        db_session.add(doc)
        await db_session.flush()
        await db_session.commit()

        pkg = await generate_export(db_session, sid)

        assert pkg["summary"]["total_documents"] == 1
        assert len(pkg["source_documents"]) == 1
        assert pkg["source_documents"][0]["filename"] == "test.pdf"

    async def test_generate_export_sorts_items_by_type(self, db_session):
        """Items should be correctly categorised as income/deduction/needs_review."""
        from app.models.tax_item import TaxItem

        sid = await self._create_session(db_session)

        # Add items
        for item_type, category, amount, needs_review in [
            ("income", "salary_wages", 85000, False),
            ("income", "bank_interest", 350, False),
            ("deduction", "tools_equipment", 149, False),
            ("deduction", "work_from_home", 520, True),
            ("out_of_scope", "other", None, True),
        ]:
            db_session.add(TaxItem(
                session_id=sid, item_type=item_type, category=category,
                amount=amount, needs_review=needs_review,
                review_reason="Test" if needs_review else None,
                confidence=0.9,
            ))
        await db_session.flush()
        await db_session.commit()

        pkg = await generate_export(db_session, sid)

        assert pkg["summary"]["total_items"] == 5
        assert pkg["summary"]["income_count"] == 2
        assert pkg["summary"]["deduction_count"] == 2
        assert pkg["summary"]["needs_review_count"] == 2  # tools_equipment is auto-approved
        assert pkg["summary"]["approved_count"] == 3  # salary + bank + tools
        assert pkg["summary"]["total_income_aud"] == 85350.0
        assert pkg["summary"]["total_candidate_deductions_aud"] == 669.0

        assert len(pkg["income_items"]) == 2
        assert len(pkg["deduction_items"]) == 2
        assert len(pkg["needs_review_items"]) == 2
        assert len(pkg["out_of_scope_items"]) == 1

    async def test_export_raises_for_missing_session(self, db_session):
        """Non-existent session should raise ValueError."""
        import pytest
        with pytest.raises(ValueError, match="Session not found"):
            await generate_export(db_session, "nonexistent-id")
