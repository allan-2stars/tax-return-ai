"""Integration tests for workspace-first upload endpoint validation/errors."""
import hashlib
import io

import pytest
from sqlalchemy import select

from app.models.document import Document


@pytest.fixture(autouse=True)
def _stub_ingestion_pipeline(monkeypatch):
    async def _noop_pipeline(*args, **kwargs):
        return None

    monkeypatch.setattr("app.routers.documents._run_ingestion_pipeline", _noop_pipeline)


class TestUploadEndpoint:
    async def _create_workspace(self, client) -> str:
        setup = await client.post("/api/auth/setup", json={"master_password": "supersecure123"})
        assert setup.status_code == 200
        workspaces = await client.get("/api/workspaces")
        assert workspaces.status_code == 200
        payload = workspaces.json()
        assert payload
        return payload[0]["id"]

    async def test_upload_file_success(self, async_client):
        workspace_id = await self._create_workspace(async_client)
        file_content = b"test receipt content"

        resp = await async_client.post(
            f"/api/workspaces/{workspace_id}/documents/upload",
            files={"file": ("receipt.txt", io.BytesIO(file_content), "text/plain")},
        )

        assert resp.status_code == 202
        data = resp.json()
        assert data["document_id"] is not None
        assert data["job_id"] is not None
        assert data["job_type"] in {"ingestion", "ingestion_pipeline"}
        assert data["job_status"] in {"queued", "running", "succeeded"}

    async def test_upload_blocks_exact_duplicate(self, async_client):
        workspace_id = await self._create_workspace(async_client)
        file_content = b"duplicate content"

        resp1 = await async_client.post(
            f"/api/workspaces/{workspace_id}/documents/upload",
            files={"file": ("original.txt", io.BytesIO(file_content), "text/plain")},
        )
        assert resp1.status_code == 202
        first_doc_id = resp1.json()["document_id"]

        resp2 = await async_client.post(
            f"/api/workspaces/{workspace_id}/documents/upload",
            files={"file": ("renamed.txt", io.BytesIO(file_content), "text/plain")},
        )
        assert resp2.status_code == 409
        payload = resp2.json()["detail"]
        assert payload["code"] == "duplicate_file"
        assert payload["retryable"] is False
        assert payload["existing_document"]["id"] == first_doc_id

    async def test_upload_same_filename_different_hash_allowed(self, async_client):
        workspace_id = await self._create_workspace(async_client)

        first = await async_client.post(
            f"/api/workspaces/{workspace_id}/documents/upload",
            files={"file": ("same.pdf", io.BytesIO(b"first"), "application/pdf")},
        )
        assert first.status_code == 202

        second = await async_client.post(
            f"/api/workspaces/{workspace_id}/documents/upload",
            files={"file": ("same.pdf", io.BytesIO(b"second"), "application/pdf")},
        )
        assert second.status_code == 202

    async def test_duplicate_upload_does_not_create_new_job(self, async_client):
        workspace_id = await self._create_workspace(async_client)
        file_content = b"duplicate content"
        resp1 = await async_client.post(
            f"/api/workspaces/{workspace_id}/documents/upload",
            files={"file": ("original.txt", io.BytesIO(file_content), "text/plain")},
        )
        assert resp1.status_code == 202

        docs_before = await async_client.get(f"/api/workspaces/{workspace_id}/documents")
        assert docs_before.status_code == 200
        count_before = len(docs_before.json())

        resp2 = await async_client.post(
            f"/api/workspaces/{workspace_id}/documents/upload",
            files={"file": ("renamed.txt", io.BytesIO(file_content), "text/plain")},
        )
        assert resp2.status_code == 409

        docs_after = await async_client.get(f"/api/workspaces/{workspace_id}/documents")
        assert docs_after.status_code == 200
        assert len(docs_after.json()) == count_before

    async def test_duplicate_reupload_allowed_when_existing_failed(self, async_client, db_session):
        workspace_id = await self._create_workspace(async_client)
        file_content = b"recoverable-failure-content"
        first = await async_client.post(
            f"/api/workspaces/{workspace_id}/documents/upload",
            files={"file": ("failed.txt", io.BytesIO(file_content), "text/plain")},
        )
        assert first.status_code == 202
        first_doc_id = first.json()["document_id"]

        row = await db_session.execute(select(Document).where(Document.id == first_doc_id))
        doc = row.scalar_one()
        doc.status = "classification_failed"
        doc.status_reason = "temporary failure"
        await db_session.commit()

        second = await async_client.post(
            f"/api/workspaces/{workspace_id}/documents/upload",
            files={"file": ("failed-retry.txt", io.BytesIO(file_content), "text/plain")},
        )
        assert second.status_code == 202

    async def test_upload_requires_auth(self, async_client):
        resp = await async_client.post(
            "/api/workspaces/w1/documents/upload",
            files={"file": ("test.txt", io.BytesIO(b"content"), "text/plain")},
        )
        assert resp.status_code == 401

    async def test_upload_empty_file_returns_400(self, async_client):
        workspace_id = await self._create_workspace(async_client)
        resp = await async_client.post(
            f"/api/workspaces/{workspace_id}/documents/upload",
            files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")},
        )
        assert resp.status_code == 400
        payload = resp.json()
        assert payload["detail"]["code"] == "empty_file"
        assert payload["detail"]["retryable"] is False

    async def test_upload_unsupported_media_returns_415(self, async_client):
        workspace_id = await self._create_workspace(async_client)
        resp = await async_client.post(
            f"/api/workspaces/{workspace_id}/documents/upload",
            files={"file": ("audio.mp3", io.BytesIO(b"ID3fake"), "audio/mpeg")},
        )
        assert resp.status_code == 415
        payload = resp.json()
        assert payload["detail"]["code"] == "unsupported_file_type"
        assert payload["detail"]["retryable"] is False
        assert "Allowed formats" in payload["detail"]["message"]

    async def test_upload_with_category_and_fy(self, async_client):
        workspace_id = await self._create_workspace(async_client)
        file_content = b"receipt for tools"

        resp = await async_client.post(
            f"/api/workspaces/{workspace_id}/documents/upload",
            data={"category": "tools_equipment", "financial_year": "2025-2026"},
            files={"file": ("tool_receipt.txt", io.BytesIO(file_content), "text/plain")},
        )

        assert resp.status_code == 202
        data = resp.json()
        assert data["document_id"] is not None

        docs = await async_client.get(f"/api/workspaces/{workspace_id}/documents")
        assert docs.status_code == 200
        doc = next(d for d in docs.json() if d["id"] == data["document_id"])
        assert doc["category"] == "tools_equipment"
        assert doc["financial_year"] == "2025-2026"

    async def test_upload_computes_correct_hash(self, async_client):
        workspace_id = await self._create_workspace(async_client)
        file_content = b"hash verification content"

        resp = await async_client.post(
            f"/api/workspaces/{workspace_id}/documents/upload",
            files={"file": ("hash_test.txt", io.BytesIO(file_content), "text/plain")},
        )

        assert resp.status_code == 202
        doc_id = resp.json()["document_id"]

        docs = await async_client.get(f"/api/workspaces/{workspace_id}/documents")
        assert docs.status_code == 200
        doc = next(d for d in docs.json() if d["id"] == doc_id)
        expected_hash = hashlib.sha256(file_content).hexdigest()
        assert doc["file_hash"] == expected_hash
