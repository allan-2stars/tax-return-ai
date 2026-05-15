from pathlib import Path

from sqlalchemy import select

from app.models.audit_log import AuditLog
from app.models.export_package import ExportPackageModel
from app.models.tax_item import TaxItem
from app.models.tax_session import TaxSession
from app.services.export.cleanup import cleanup_deleted_review_packs


async def _setup_workspace(async_client):
    res = await async_client.post("/api/auth/setup", json={"master_password": "supersecure123"})
    assert res.status_code == 200
    ws = await async_client.get("/api/workspaces")
    assert ws.status_code == 200
    return ws.json()[0]["id"]


async def _ensure_session(async_client, db_session, workspace_id: str):
    ensure = await async_client.get(f"/api/workspaces/{workspace_id}/items")
    assert ensure.status_code == 200
    row = await db_session.execute(select(TaxSession).where(TaxSession.workspace_id == workspace_id))
    return row.scalar_one()


async def _seed_ready_item(db_session, session_id: str):
    item = TaxItem(
        session_id=session_id,
        item_type="deduction",
        category="tools_equipment",
        amount=55,
        description="tool",
        needs_review=False,
        review_status="confirmed",
    )
    db_session.add(item)
    await db_session.commit()


async def test_workspace_audit_events_requires_auth(async_client):
    res = await async_client.get("/api/workspaces/w1/audit-events")
    assert res.status_code == 401


async def test_workspace_audit_events_returns_newest_first(async_client, db_session):
    workspace_id = await _setup_workspace(async_client)
    session = await _ensure_session(async_client, db_session, workspace_id)
    await _seed_ready_item(db_session, session.id)

    gen = await async_client.post(
        f"/api/workspaces/{workspace_id}/review-pack/generate",
        json={"export_password": "verystrongpass123", "include_source_documents": False},
    )
    assert gen.status_code == 200
    export_id = gen.json()["id"]

    deleted = await async_client.delete(f"/api/workspaces/{workspace_id}/review-pack/{export_id}")
    assert deleted.status_code == 200

    events = await async_client.get(f"/api/workspaces/{workspace_id}/audit-events?limit=5")
    assert events.status_code == 200
    payload = events.json()
    assert len(payload) >= 2
    assert payload[0]["created_at"] >= payload[1]["created_at"]
    assert any(event["action"] == "review_pack_deleted" for event in payload)


async def test_cleanup_deleted_review_packs_removes_leftover_file(async_client, db_session):
    workspace_id = await _setup_workspace(async_client)
    session = await _ensure_session(async_client, db_session, workspace_id)
    await _seed_ready_item(db_session, session.id)

    gen = await async_client.post(
        f"/api/workspaces/{workspace_id}/review-pack/generate",
        json={"export_password": "verystrongpass123", "include_source_documents": False},
    )
    assert gen.status_code == 200
    export_id = gen.json()["id"]

    row = await db_session.execute(select(ExportPackageModel).where(ExportPackageModel.id == export_id))
    record = row.scalar_one()
    path = Path(record.storage_path)
    assert path.exists()

    record.status = "deleted"
    await db_session.commit()

    result = await cleanup_deleted_review_packs(db_session)
    await db_session.commit()
    assert result.deleted_file_count >= 1
    assert not path.exists()

    row2 = await db_session.execute(select(ExportPackageModel).where(ExportPackageModel.id == export_id))
    record2 = row2.scalar_one()
    assert record2.storage_path is None


async def test_download_audit_event_written(async_client, db_session):
    workspace_id = await _setup_workspace(async_client)
    session = await _ensure_session(async_client, db_session, workspace_id)
    await _seed_ready_item(db_session, session.id)

    gen = await async_client.post(
        f"/api/workspaces/{workspace_id}/review-pack/generate",
        json={"export_password": "verystrongpass123", "include_source_documents": False},
    )
    assert gen.status_code == 200
    export_id = gen.json()["id"]

    dl = await async_client.get(f"/api/workspaces/{workspace_id}/review-pack/{export_id}/download")
    assert dl.status_code == 200

    logs = await db_session.execute(
        select(AuditLog).where(AuditLog.entity_id == export_id, AuditLog.action == "review_pack_downloaded")
    )
    assert logs.scalar_one_or_none() is not None

