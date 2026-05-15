"""CRUD integration tests for all API endpoints — sessions, documents, items, audit."""
import pytest


class TestSessions:
    """Tax session CRUD tests."""

    async def test_create_session(self, async_client):
        resp = await async_client.post("/api/sessions", json={
            "title": "Test Session",
            "financial_year": "2025-2026",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Test Session"
        assert data["financial_year"] == "2025-2026"
        assert data["status"] == "draft"
        assert "id" in data
        return data["id"]

    async def test_list_sessions(self, async_client):
        await async_client.post("/api/sessions", json={"title": "S1"})
        await async_client.post("/api/sessions", json={"title": "S2"})
        resp = await async_client.get("/api/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2

    async def test_get_session(self, async_client):
        sid = await self.test_create_session(async_client)
        resp = await async_client.get(f"/api/sessions/{sid}")
        assert resp.status_code == 200
        assert resp.json()["id"] == sid

    async def test_get_session_not_found(self, async_client):
        resp = await async_client.get("/api/sessions/nonexistent")
        assert resp.status_code == 404

    async def test_update_session(self, async_client):
        sid = await self.test_create_session(async_client)
        resp = await async_client.patch(f"/api/sessions/{sid}", json={
            "title": "Updated", "notes": "Some notes"
        })
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated"
        assert resp.json()["notes"] == "Some notes"

    async def test_delete_session(self, async_client):
        sid = await self.test_create_session(async_client)
        resp = await async_client.delete(f"/api/sessions/{sid}")
        assert resp.status_code == 204
        # Verify it's gone
        resp = await async_client.get(f"/api/sessions/{sid}")
        assert resp.status_code == 404


class TestDocuments:
    """Document CRUD tests."""

    async def _create_session(self, client):
        resp = await client.post("/api/sessions", json={"title": "Doc Test"})
        return resp.json()["id"]

    async def test_create_document(self, async_client):
        sid = await self._create_session(async_client)
        resp = await async_client.post("/api/documents", json={
            "session_id": sid,
            "original_filename": "receipt.pdf",
            "mime_type": "application/pdf",
            "file_size_bytes": 12345,
            "file_hash": "a" * 64,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["original_filename"] == "receipt.pdf"
        assert data["status"] == "uploaded"
        assert data["session_id"] == sid
        return data["id"]

    async def test_list_documents_by_session(self, async_client):
        sid = await self._create_session(async_client)
        await async_client.post("/api/documents", json={
            "session_id": sid, "original_filename": "f1.pdf",
            "mime_type": "application/pdf", "file_size_bytes": 100,
        })
        await async_client.post("/api/documents", json={
            "session_id": sid, "original_filename": "f2.pdf",
            "mime_type": "application/pdf", "file_size_bytes": 200,
        })
        resp = await async_client.get(f"/api/documents?session_id={sid}")
        assert resp.status_code == 200
        assert len(resp.json()) >= 2

    async def test_update_document_status(self, async_client):
        sid = await self._create_session(async_client)
        did = await self.test_create_document(async_client)
        resp = await async_client.patch(f"/api/documents/{did}", json={
            "status": "processing"
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "processing"

    async def test_delete_document(self, async_client):
        did = await self.test_create_document(async_client)
        resp = await async_client.delete(f"/api/documents/{did}")
        assert resp.status_code == 204


class TestItems:
    """Tax item CRUD + review tests."""

    async def _create_session(self, client):
        resp = await client.post("/api/sessions", json={"title": "Item Test"})
        return resp.json()["id"]

    async def test_create_item(self, async_client):
        sid = await self._create_session(async_client)
        resp = await async_client.post("/api/items", json={
            "session_id": sid,
            "item_type": "income",
            "category": "salary_wages",
            "amount": 95000.0,
            "description": "Annual salary",
            "confidence": 0.95,
            "needs_review": True,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["item_type"] == "income"
        assert data["category"] == "salary_wages"
        assert data["needs_review"] is True
        return data["id"]

    async def test_list_items_filtered(self, async_client):
        sid = await self._create_session(async_client)
        await async_client.post("/api/items", json={
            "session_id": sid, "item_type": "income",
            "category": "salary_wages", "amount": 50000, "needs_review": False,
        })
        await async_client.post("/api/items", json={
            "session_id": sid, "item_type": "deduction",
            "category": "tools_equipment", "amount": 150, "needs_review": True,
        })
        # Filter by type
        resp = await async_client.get(f"/api/items?session_id={sid}&item_type=income")
        assert len(resp.json()) == 1
        # Filter by review status
        resp = await async_client.get(f"/api/items?session_id={sid}&needs_review=true")
        assert len(resp.json()) == 1

    async def test_review_item_approve(self, async_client):
        sid = await self._create_session(async_client)
        iid = await self.test_create_item(async_client)
        resp = await async_client.post(f"/api/items/{iid}/review", json={
            "needs_review": False,
            "review_reason": "User confirmed this is correct",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["needs_review"] is False
        assert data["review_reason"] == "User confirmed this is correct"

    async def test_review_item_flag(self, async_client):
        sid = await self._create_session(async_client)
        iid = await self.test_create_item(async_client)
        resp = await async_client.post(f"/api/items/{iid}/review", json={
            "needs_review": True,
            "review_reason": "Missing evidence",
        })
        assert resp.status_code == 200
        assert resp.json()["needs_review"] is True

    async def test_delete_item(self, async_client):
        iid = await self.test_create_item(async_client)
        resp = await async_client.delete(f"/api/items/{iid}")
        assert resp.status_code == 204


class TestAudit:
    """Audit log tests."""

    async def test_create_session_writes_audit(self, async_client):
        """Creating a session should produce an audit log entry."""
        resp = await async_client.post("/api/sessions", json={"title": "Audit Test"})
        sid = resp.json()["id"]
        resp = await async_client.get("/api/audit")
        entries = resp.json()
        matching = [e for e in entries if e["entity_id"] == sid]
        assert len(matching) >= 1
        assert matching[0]["action"] == "created"
        assert matching[0]["entity_type"] == "tax_session"

    async def test_audit_filter(self, async_client):
        resp = await async_client.get("/api/audit?entity_type=tax_session&limit=10")
        assert resp.status_code == 200
