"""Tests for the compliance review service.

Covers:
  - run_compliance_review: end-to-end review via DB
  - _review_item, _assess_risk, _assess_evidence: pure logic
"""
from app.services.compliance_review import (
    run_compliance_review,
    _review_item,
    _assess_risk,
    _assess_evidence,
)


class TestRiskAssessment:
    """Pure function tests for _assess_risk."""

    def _make_item(self, needs_review=False, category="salary_wages", confidence=0.95):
        from types import SimpleNamespace
        return SimpleNamespace(
            id="test-id", item_type="income", category=category,
            amount=1000.0, description="Test", confidence=confidence,
            needs_review=needs_review, review_reason=None,
            ato_reference_hint=None,
        )

    def test_auto_approved_high_conf_low_risk(self):
        item = self._make_item(needs_review=False, confidence=0.95)
        assert _assess_risk(item) == "low"

    def test_high_risk_categories_with_review(self):
        item = self._make_item(needs_review=True, category="mixed_use")
        assert _assess_risk(item) == "high"

    def test_other_category_with_review(self):
        item = self._make_item(needs_review=True, category="other")
        assert _assess_risk(item) == "high"

    def test_needs_review_medium(self):
        item = self._make_item(needs_review=True, category="tools_equipment")
        assert _assess_risk(item) == "medium"

    def test_low_confidence_auto_approved_medium(self):
        item = self._make_item(needs_review=False, confidence=0.5)
        assert _assess_risk(item) == "medium"


class TestEvidenceAssessment:
    """Pure function tests for _assess_evidence."""

    def _make_item(self, needs_review=False, category="salary_wages", amount=1000.0):
        from types import SimpleNamespace
        return SimpleNamespace(
            id="test-id", item_type="income", category=category,
            amount=amount, description="Test", confidence=0.95,
            needs_review=needs_review, review_reason=None,
            ato_reference_hint=None,
        )

    def test_complete_evidence(self):
        assert _assess_evidence(self._make_item()) == "complete"

    def test_partial_for_mixed_use(self):
        assert _assess_evidence(self._make_item(category="mixed_use")) == "partial"

    def test_partial_for_donation(self):
        assert _assess_evidence(self._make_item(category="donation")) == "partial"

    def test_partial_for_needs_review(self):
        assert _assess_evidence(self._make_item(needs_review=True)) == "partial"

    def test_missing_for_no_amount(self):
        assert _assess_evidence(self._make_item(amount=None)) == "missing_or_incomplete"


class TestReviewItem:
    """Pure function tests for _review_item."""

    def _make_item(self, needs_review=False, category="salary_wages",
                   amount=1000.0, confidence=0.95, item_type="income",
                   description="Annual salary"):
        from types import SimpleNamespace
        return SimpleNamespace(
            id="item-001", item_type=item_type, category=category,
            amount=amount, description=description, confidence=confidence,
            needs_review=needs_review,
            review_reason="Low confidence" if needs_review and confidence < 0.7 else None,
            ato_reference_hint=None,
        )

    def test_clean_item_minimal_findings(self):
        review = _review_item(self._make_item(), "2025-2026")
        assert review["risk_level"] == "low"
        assert review["evidence_status"] == "complete"
        assert review["review_status"] == "user_confirmed"
        assert review["requires_tax_agent"] is False

    def test_needs_review_item_has_actions(self):
        review = _review_item(
            self._make_item(needs_review=True, confidence=0.6, category="tools_equipment"),
            "2025-2026",
        )
        assert review["review_status"] == "needs_user_review"
        assert len(review["findings"]) >= 1
        assert len(review["required_actions"]) >= 1

    def test_mixed_use_triggers_tax_agent(self):
        review = _review_item(
            self._make_item(needs_review=True, category="mixed_use"),
            "2025-2026",
        )
        assert review["requires_tax_agent"] is True
        assert "apportionment" in review["tax_agent_reason"].lower()

    def test_no_amount_adds_finding(self):
        review = _review_item(
            self._make_item(amount=None),
            "2025-2026",
        )
        findings = " ".join(review["findings"])
        assert "no dollar amount" in findings.lower()


class TestComplianceReviewService:
    """Integration tests requiring DB."""

    async def _create_session(self, db):
        from app.models.tax_session import TaxSession
        s = TaxSession(title="Compliance Test", financial_year="2025-2026")
        db.add(s)
        await db.flush()
        return s.id

    async def test_compliance_review_basic_shape(self, db_session):
        """Verify the output matches the schema shape."""
        sid = await self._create_session(db_session)

        result = await run_compliance_review(db_session, sid)

        assert result["schema_version"] == "1.1"
        assert result["tax_session_id"] == sid
        assert result["financial_year"] == "2025-2026"
        assert "generated_at" in result
        assert "review_status" in result
        assert "export_readiness" in result
        assert "summary" in result
        assert "items" in result
        assert "unresolved_questions" in result
        assert "tax_agent_review_triggers" in result

    async def test_empty_session_ready_for_export(self, db_session):
        """An empty session with no items is export-ready."""
        sid = await self._create_session(db_session)

        result = await run_compliance_review(db_session, sid)

        assert result["review_status"] == "completed"
        assert result["export_readiness"]["status"] == "ready_for_human_review_export"

    async def test_needs_review_item_blocks_export(self, db_session):
        """Items needing review should block export readiness."""
        from app.models.tax_item import TaxItem

        sid = await self._create_session(db_session)
        db_session.add(TaxItem(
            session_id=sid, item_type="deduction", category="tools_equipment",
            amount=149.0, needs_review=True, review_reason="Low confidence",
            confidence=0.6,
        ))
        await db_session.flush()
        await db_session.commit()

        result = await run_compliance_review(db_session, sid)

        assert result["review_status"] == "in_progress"
        assert result["export_readiness"]["status"] == "not_export_ready"
        assert "1 item" in result["export_readiness"]["reason"]

    async def test_high_risk_triggers_tax_agent(self, db_session):
        """Mixed-use items needing review should trigger tax agent referral."""
        from app.models.tax_item import TaxItem

        sid = await self._create_session(db_session)
        db_session.add(TaxItem(
            session_id=sid, item_type="deduction", category="mixed_use",
            amount=2000.0, needs_review=True,
            review_reason="Mixed use — personal/work split unknown",
            confidence=0.65,
        ))
        await db_session.flush()
        await db_session.commit()

        result = await run_compliance_review(db_session, sid)

        assert len(result["tax_agent_review_triggers"]) >= 1
        assert "apportionment" in result["tax_agent_review_triggers"][0].lower()

    async def test_summary_counts(self, db_session):
        """Summary should correctly count items by type and risk."""
        from app.models.tax_item import TaxItem

        sid = await self._create_session(db_session)
        items_data = [
            ("income", "salary_wages", 85000, False, 0.95),
            ("deduction", "union_fee", 450, False, 0.92),
            ("deduction", "tools_equipment", 149, False, 0.72),
            ("deduction", "mixed_use", 2000, True, 0.65),
        ]
        for item_type, category, amount, needs_review, confidence in items_data:
            db_session.add(TaxItem(
                session_id=sid, item_type=item_type, category=category,
                amount=amount, needs_review=needs_review,
                confidence=confidence,
            ))
        await db_session.flush()
        await db_session.commit()

        result = await run_compliance_review(db_session, sid)

        assert result["summary"]["income_items"] == 1
        assert result["summary"]["deduction_items"] == 3
        assert result["summary"]["risk_counts"]["low"] == 1   # salary_wages
        assert result["summary"]["risk_counts"]["medium"] == 2  # union_fee + tools
        assert result["summary"]["risk_counts"]["high"] == 1   # mixed_use

    async def test_compliance_raises_for_missing_session(self, db_session):
        import pytest
        with pytest.raises(ValueError, match="Session not found"):
            await run_compliance_review(db_session, "nonexistent")
