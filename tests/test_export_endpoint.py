"""Integration tests for the export and compliance endpoints.

Covers:
  - GET /api/export/:session_id — export package generation
  - GET /api/compliance/:session_id — compliance review
  - Error handling for missing sessions
"""


class TestExportEndpoint:
    """Tests for GET /api/export/:session_id."""

    async def _create_session(self, client):
        resp = await client.post("/api/sessions", json={
            "title": "Export Endpoint Test", "financial_year": "2025-2026",
        })
        return resp.json()["id"]

    async def test_export_empty_session(self, async_client):
        sid = await self._create_session(async_client)
        resp = await async_client.get(f"/api/export/{sid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session"]["id"] == sid
        assert data["summary"]["total_documents"] == 0
        assert data["summary"]["total_items"] == 0
        assert len(data["export_warnings"]) == 0

    async def test_export_with_items(self, async_client):
        sid = await self._create_session(async_client)

        # Create an item via API
        await async_client.post("/api/items", json={
            "session_id": sid, "item_type": "income",
            "category": "salary_wages", "amount": 85000,
            "description": "Annual salary", "confidence": 0.95,
            "needs_review": False,
        })

        resp = await async_client.get(f"/api/export/{sid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"]["total_items"] == 1
        assert data["summary"]["income_count"] == 1
        assert data["summary"]["total_income_aud"] == 85000.0
        assert len(data["income_items"]) == 1
        assert data["income_items"][0]["category"] == "salary_wages"

    async def test_export_not_found(self, async_client):
        resp = await async_client.get("/api/export/nonexistent")
        assert resp.status_code == 404


class TestComplianceEndpoint:
    """Tests for GET /api/compliance/:session_id."""

    async def _create_session(self, client):
        resp = await client.post("/api/sessions", json={
            "title": "Compliance Endpoint Test", "financial_year": "2025-2026",
        })
        return resp.json()["id"]

    async def test_compliance_empty_session(self, async_client):
        sid = await self._create_session(async_client)
        resp = await async_client.get(f"/api/compliance/{sid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["schema_version"] == "1.1"
        assert data["review_status"] == "completed"
        assert data["export_readiness"]["status"] == "ready_for_human_review_export"
        assert len(data["items"]) == 0

    async def test_compliance_with_needs_review_items(self, async_client):
        sid = await self._create_session(async_client)

        # Add an item needing review
        await async_client.post("/api/items", json={
            "session_id": sid, "item_type": "deduction",
            "category": "tools_equipment", "amount": 149.0,
            "description": "USB hub", "confidence": 0.6,
            "needs_review": True, "review_reason": "Low confidence",
        })

        resp = await async_client.get(f"/api/compliance/{sid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["review_status"] == "in_progress"
        assert data["export_readiness"]["status"] == "not_export_ready"
        assert len(data["items"]) == 1
        assert data["items"][0]["requires_tax_agent"] is False  # tools_equipment isn't agent-category

    async def test_compliance_with_high_risk_item(self, async_client):
        sid = await self._create_session(async_client)

        await async_client.post("/api/items", json={
            "session_id": sid, "item_type": "deduction",
            "category": "mixed_use", "amount": 2000.0,
            "description": "Laptop for work/personal", "confidence": 0.65,
            "needs_review": True,
            "review_reason": "Mixed use — work percentage unknown",
        })

        resp = await async_client.get(f"/api/compliance/{sid}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["tax_agent_review_triggers"]) >= 1
        assert "apportionment" in data["tax_agent_review_triggers"][0].lower()

    async def test_compliance_not_found(self, async_client):
        resp = await async_client.get("/api/compliance/nonexistent")
        assert resp.status_code == 404
