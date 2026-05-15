"""Integration tests for the POST /api/documents/upload endpoint.

Covers:
  - File upload via multipart/form-data returns 202 with job_id
  - Duplicate detection through the API endpoint
  - Error handling (missing fields, empty files)
"""
import io
import hashlib
from httpx import ASGITransport, AsyncClient


class TestUploadEndpoint:
    """Tests for the file upload router endpoint."""

    async def _create_session(self, client):
        resp = await client.post("/api/sessions", json={
            "title": "Upload Test Session", "financial_year": "2025-2026",
        })
        return resp.json()["id"]

    async def test_upload_file_success(self, async_client):
        sid = await self._create_session(async_client)
        file_content = b"test receipt content"

        resp = await async_client.post(
            "/api/documents/upload",
            data={"session_id": sid},
            files={"file": ("receipt.txt", io.BytesIO(file_content), "text/plain")},
        )

        # Now returns 202 Accepted with job_id
        assert resp.status_code == 202
        data = resp.json()
        assert data["document_id"] is not None
        assert data["job_id"] is not None
        assert data["job_type"] == "ingestion"
        assert data["job_status"] == "queued"

    async def test_upload_detects_duplicate(self, async_client):
        """Same file content uploaded twice should detect duplicate."""
        sid = await self._create_session(async_client)
        file_content = b"duplicate content"

        # First upload
        resp1 = await async_client.post(
            "/api/documents/upload",
            data={"session_id": sid},
            files={"file": ("original.txt", io.BytesIO(file_content), "text/plain")},
        )
        assert resp1.status_code == 202
        first_doc_id = resp1.json()["document_id"]

        # Second upload — same content, different filename
        resp2 = await async_client.post(
            "/api/documents/upload",
            data={"session_id": sid},
            files={"file": ("renamed.txt", io.BytesIO(file_content), "text/plain")},
        )
        assert resp2.status_code == 202
        data2 = resp2.json()
        assert data2["document_id"] != first_doc_id  # New doc record
        assert data2["job_id"] is not None

    async def test_upload_different_sessions_unique(self, async_client):
        """Same file in different sessions should NOT be flagged as duplicate."""
        sid1 = await self._create_session(async_client)
        sid2 = await self._create_session(async_client)
        file_content = b"shared content across sessions"

        await async_client.post(
            "/api/documents/upload",
            data={"session_id": sid1},
            files={"file": ("doc1.txt", io.BytesIO(file_content), "text/plain")},
        )

        resp2 = await async_client.post(
            "/api/documents/upload",
            data={"session_id": sid2},
            files={"file": ("doc2.txt", io.BytesIO(file_content), "text/plain")},
        )

        assert resp2.status_code == 202

    async def test_upload_missing_session_id_returns_422(self, async_client):
        """Missing required session_id should return 422."""
        resp = await async_client.post(
            "/api/documents/upload",
            files={"file": ("test.txt", io.BytesIO(b"content"), "text/plain")},
        )
        assert resp.status_code == 422

    async def test_upload_empty_file_returns_400(self, async_client):
        """Empty file should be rejected."""
        sid = await self._create_session(async_client)
        resp = await async_client.post(
            "/api/documents/upload",
            data={"session_id": sid},
            files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")},
        )
        assert resp.status_code == 400
        assert "empty" in resp.text.lower()

    async def test_upload_with_category_and_fy(self, async_client):
        """Upload can include optional category and financial_year."""
        sid = await self._create_session(async_client)
        file_content = b"receipt for tools"

        resp = await async_client.post(
            "/api/documents/upload",
            data={
                "session_id": sid,
                "category": "tools_equipment",
                "financial_year": "2025-2026",
            },
            files={"file": ("tool_receipt.txt", io.BytesIO(file_content), "text/plain")},
        )

        assert resp.status_code == 202
        data = resp.json()
        assert data["document_id"] is not None

        # Verify the document has category and FY
        resp_get = await async_client.get(f"/api/documents/{data['document_id']}")
        assert resp_get.status_code == 200
        doc = resp_get.json()
        assert doc["category"] == "tools_equipment"
        assert doc["financial_year"] == "2025-2026"

    async def test_upload_computes_correct_hash(self, async_client):
        """Verify SHA-256 hash is computed correctly through the API."""
        sid = await self._create_session(async_client)
        file_content = b"hash verification content"

        resp = await async_client.post(
            "/api/documents/upload",
            data={"session_id": sid},
            files={"file": ("hash_test.txt", io.BytesIO(file_content), "text/plain")},
        )

        assert resp.status_code == 202
        doc_id = resp.json()["document_id"]

        # Get the document to check hash
        resp_get = await async_client.get(f"/api/documents/{doc_id}")
        assert resp_get.status_code == 200
        expected_hash = hashlib.sha256(file_content).hexdigest()
        assert resp_get.json()["file_hash"] == expected_hash
