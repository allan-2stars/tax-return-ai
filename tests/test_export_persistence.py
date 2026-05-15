"""Tests for export persistence and compliance endpoint integration.

Covers:
  - ExportPackageModel persistence after generate_export
  - Export history endpoint returns list of past exports
  - CSV export endpoint returns proper content type and headers
  - Compliance endpoint returns structured review for valid sessions
  - Compliance endpoint with items returns item-level reviews
  - 404 handling for missing sessions
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient
from app.models.tax_session import TaxSession
from app.models.document import Document
from app.models.tax_item import TaxItem
from app.models.export_package import ExportPackageModel
from app.services.export import generate_export


class TestExportPersistence:
    """Tests for export_packages table persistence."""

    async def _setup_session_with_items(self, db: AsyncSession):
        session = TaxSession(title="Export Test", financial_year="2025-2026")
        db.add(session)
        await db.flush()

        doc = Document(
            session_id=session.id,
            original_filename="test.txt",
            mime_type="text/plain",
            file_size_bytes=100,
            status="classified",
        )
        db.add(doc)
        await db.flush()

        income = TaxItem(
            session_id=session.id,
            item_type="income",
            category="salary_wages",
            amount=85000.0,
            description="Annual salary",
            confidence=0.95,
            needs_review=False,
        )
        db.add(income)

        deduction = TaxItem(
            session_id=session.id,
            item_type="deduction",
            category="tools_equipment",
            amount=350.0,
            description="Office supplies",
            confidence=0.70,
            needs_review=True,
            review_reason="Work-use percentage not confirmed.",
        )
        db.add(deduction)
        await db.flush()
        await db.commit()
        return session.id

    async def test_export_creates_db_record(self, db_session):
        """Generating an export should create a record in export_packages."""
        sid = await self._setup_session_with_items(db_session)

        pkg = await generate_export(db_session, sid)

        # Verify export record was saved
        result = await db_session.execute(
            select(ExportPackageModel).where(
                ExportPackageModel.session_id == sid
            )
        )
        records = result.scalars().all()
        assert len(records) >= 1
        record = records[0]
        assert record.format == "json"
        assert record.item_count >= 2
        assert record.export_data is not None
        assert record.session_id == sid

    async def test_export_record_has_correct_item_count(self, db_session):
        """Export package should reflect correct item count."""
        sid = await self._setup_session_with_items(db_session)

        pkg = await generate_export(db_session, sid)

        result = await db_session.execute(
            select(ExportPackageModel).where(
                ExportPackageModel.session_id == sid
            )
        )
        record = result.scalar_one_or_none()
        assert record is not None
        assert record.item_count == 2

    async def test_export_record_has_totals(self, db_session):
        """Export package should track total amounts."""
        sid = await self._setup_session_with_items(db_session)

        pkg = await generate_export(db_session, sid)

        result = await db_session.execute(
            select(ExportPackageModel).where(
                ExportPackageModel.session_id == sid
            )
        )
        record = result.scalar_one_or_none()
        assert record is not None
        # total_amount should reflect deductions
        assert record.total_amount == 350.0

    async def test_multiple_exports_create_multiple_records(self, db_session):
        """Multiple export calls should create multiple records."""
        sid = await self._setup_session_with_items(db_session)

        await generate_export(db_session, sid)
        await generate_export(db_session, sid)

        result = await db_session.execute(
            select(ExportPackageModel).where(
                ExportPackageModel.session_id == sid
            )
        )
        records = result.scalars().all()
        assert len(records) == 2


class TestExportHistoryEndpoint:
    """Tests for the export history endpoint."""

    async def test_export_history_empty(self, async_client):
        """GET /api/export/:id/history with no exports returns empty list."""
        resp = await async_client.post("/api/sessions", json={
            "title": "History Test", "financial_year": "2025-2026",
        })
        sid = resp.json()["id"]

        resp = await async_client.get(f"/api/export/{sid}/history")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 0

    async def test_export_history_after_export(self, async_client):
        """GET /api/export/:id/history should list exports."""
        resp = await async_client.post("/api/sessions", json={
            "title": "History Test", "financial_year": "2025-2026",
        })
        sid = resp.json()["id"]

        # Generate export
        await async_client.get(f"/api/export/{sid}")

        # Check history
        resp = await async_client.get(f"/api/export/{sid}/history")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["format"] == "json"
        assert data[0]["item_count"] == 0

    async def test_export_history_multiple(self, async_client):
        """Multiple exports should all appear in history."""
        resp = await async_client.post("/api/sessions", json={
            "title": "History Multi", "financial_year": "2025-2026",
        })
        sid = resp.json()["id"]

        # Generate export twice
        await async_client.get(f"/api/export/{sid}")
        await async_client.get(f"/api/export/{sid}")

        resp = await async_client.get(f"/api/export/{sid}/history")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2


class TestCSVExportEndpoint:
    """Tests for CSV export format."""

    async def test_csv_export_endpoint(self, async_client):
        """GET /api/export/:id?format=csv should return CSV."""
        resp = await async_client.post("/api/sessions", json={
            "title": "CSV Test", "financial_year": "2025-2026",
        })
        sid = resp.json()["id"]

        resp = await async_client.get(f"/api/export/{sid}?format=csv")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in resp.headers.get("content-disposition", "")
        body = resp.text
        assert "Type" in body
        assert "Category" in body

    async def test_csv_with_items(self, async_client):
        """CSV export with items should include them in rows."""
        resp = await async_client.post("/api/sessions", json={
            "title": "CSV Items", "financial_year": "2025-2026",
        })
        sid = resp.json()["id"]

        # Add an item
        await async_client.post("/api/items", json={
            "session_id": sid, "item_type": "income",
            "category": "salary_wages", "amount": 85000,
            "description": "Annual salary", "confidence": 0.95,
            "needs_review": False,
        })

        resp = await async_client.get(f"/api/export/{sid}?format=csv")
        assert resp.status_code == 200
        body = resp.text
        assert "Income" in body
        assert "salary_wages" in body
        assert "85000" in body


class TestComplianceEndpoint:
    """Tests for the compliance review endpoint."""

    async def test_compliance_endpoint_returns_200(self, async_client):
        """GET /api/compliance/:sessionId should return 200 for valid sessions."""
        resp = await async_client.post("/api/sessions", json={
            "title": "Compliance Test", "financial_year": "2025-2026",
        })
        sid = resp.json()["id"]

        resp = await async_client.get(f"/api/compliance/{sid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["schema_version"] == "1.1"
        assert data["tax_session_id"] == sid
        assert "review_status" in data
        assert "summary" in data
        assert "items" in data
        assert "unresolved_questions" in data
        assert "tax_agent_review_triggers" in data

    async def test_compliance_with_items(self, async_client):
        """Compliance with items should return item-level reviews."""
        resp = await async_client.post("/api/sessions", json={
            "title": "Compliance Items", "financial_year": "2025-2026",
        })
        sid = resp.json()["id"]

        # Create a classified item via the API
        await async_client.post("/api/items", json={
            "session_id": sid, "item_type": "deduction",
            "category": "tools_equipment", "amount": 149.0,
            "description": "USB hub", "confidence": 0.6,
            "needs_review": True, "review_reason": "Low confidence",
        })

        # Run compliance
        resp = await async_client.get(f"/api/compliance/{sid}")
        assert resp.status_code == 200
        data = resp.json()
        # Summary has income_items, deduction_items, etc. — not total_items directly
        assert data["summary"]["income_items"] == 0
        assert data["summary"]["deduction_items"] == 1
        assert len(data["items"]) == 1
        item = data["items"][0]
        assert "risk_level" in item
        assert "findings" in item
        assert item["category"] == "tools_equipment"

    async def test_compliance_with_income_item(self, async_client):
        """Compliance with a clean income item should have low risk."""
        resp = await async_client.post("/api/sessions", json={
            "title": "Compliance Income", "financial_year": "2025-2026",
        })
        sid = resp.json()["id"]

        await async_client.post("/api/items", json={
            "session_id": sid, "item_type": "income",
            "category": "salary_wages", "amount": 85000.0,
            "description": "Annual salary", "confidence": 0.95,
            "needs_review": False,
        })

        resp = await async_client.get(f"/api/compliance/{sid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"]["income_items"] == 1
        assert data["summary"]["risk_counts"]["low"] == 1

    async def test_compliance_with_mixed_use_high_risk(self, async_client):
        """Mixed-use items needing review should trigger tax agent referral."""
        resp = await async_client.post("/api/sessions", json={
            "title": "Compliance High Risk", "financial_year": "2025-2026",
        })
        sid = resp.json()["id"]

        await async_client.post("/api/items", json={
            "session_id": sid, "item_type": "deduction",
            "category": "mixed_use", "amount": 2000.0,
            "description": "Laptop for work and personal",
            "confidence": 0.65, "needs_review": True,
            "review_reason": "Mixed use — personal/work split unknown",
        })

        resp = await async_client.get(f"/api/compliance/{sid}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["tax_agent_review_triggers"]) >= 1
        trigger = data["tax_agent_review_triggers"][0].lower()
        assert "apportionment" in trigger or "mixed" in trigger

    async def test_compliance_returns_404_for_missing_session(self, async_client):
        """GET /api/compliance/:sessionId should return 404 for missing sessions."""
        resp = await async_client.get("/api/compliance/nonexistent-id")
        assert resp.status_code == 404

    async def test_compliance_empty_session_ready(self, async_client):
        """Empty session should be marked as completed and export-ready."""
        resp = await async_client.post("/api/sessions", json={
            "title": "Empty Compliance", "financial_year": "2025-2026",
        })
        sid = resp.json()["id"]

        resp = await async_client.get(f"/api/compliance/{sid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["review_status"] == "completed"
        assert data["export_readiness"]["status"] == "ready_for_human_review_export"
