from datetime import datetime, timedelta, timezone
from sqlalchemy import select

from app.models.document import Document
from app.models.document_page import DocumentPage
from app.models.tax_item import TaxItem
from app.models.tax_session import TaxSession
from app.models.classification_result import ClassificationResultModel
from app.models.job import Job
from app.config import settings
from app.services.security.field_encryption import encrypt_text, decrypt_text
from app.services.security.key_cache import cache_session_key, clear_session_key
from scripts.backfill_encrypt_sensitive_fields import backfill_sensitive_fields
from app.services.security.key_cache import get_session_key
from app.services.classification import classify_document
from app.services.security.field_encryption import EncryptionKeyUnavailableError
from app.services.ingestion.pipeline import process_upload


async def _setup_workspace(async_client):
    res = await async_client.post("/api/auth/setup", json={"master_password": "supersecure123"})
    assert res.status_code == 200
    ws = await async_client.get("/api/workspaces")
    assert ws.status_code == 200
    return ws.json()[0]["id"]


async def _session_and_token(async_client, db_session, workspace_id: str):
    ensure = await async_client.get(f"/api/workspaces/{workspace_id}/items")
    assert ensure.status_code == 200
    row = await db_session.execute(select(TaxSession).where(TaxSession.workspace_id == workspace_id))
    session = row.scalar_one()
    session_res = await async_client.get("/api/auth/session")
    assert session_res.status_code == 200
    token = async_client.cookies.get("taxai_session")
    return session, token


def test_encrypt_decrypt_round_trip():
    key = b"k" * 32
    ct = encrypt_text("hello", key)
    assert ct is not None
    assert ct != "hello"
    pt = decrypt_text(ct, key)
    assert pt == "hello"


def test_different_nonce_changes_ciphertext():
    key = b"k" * 32
    c1 = encrypt_text("same", key)
    c2 = encrypt_text("same", key)
    assert c1 != c2


def test_tamper_detection_fails():
    key = b"k" * 32
    ct = encrypt_text("hello", key)
    assert ct is not None
    bad = ct[:-2] + "xx"
    try:
        decrypt_text(bad, key)
        assert False, "tamper should fail"
    except Exception:
        assert True


def test_null_empty_handling():
    key = b"k" * 32
    assert encrypt_text(None, key) is None
    assert encrypt_text("", key) == ""
    assert decrypt_text(None, key) is None
    assert decrypt_text("", key) == ""


async def test_encrypted_document_page_workspace_read(async_client, db_session):
    workspace_id = await _setup_workspace(async_client)
    session, token = await _session_and_token(async_client, db_session, workspace_id)
    key = b"k" * 32
    cache_session_key(token, "unused", key, datetime.now(timezone.utc) + timedelta(hours=1))

    doc = Document(
        session_id=session.id,
        original_filename="a.pdf",
        mime_type="application/pdf",
        file_size_bytes=1,
        status="uploaded",
        financial_year=session.financial_year,
    )
    db_session.add(doc)
    await db_session.flush()
    page = DocumentPage(document_id=doc.id, page_number=1, text=None, text_enc=encrypt_text("secret page", key))
    db_session.add(page)
    await db_session.commit()

    res = await async_client.get(f"/api/workspaces/{workspace_id}/documents/{doc.id}/pages")
    assert res.status_code == 200
    assert res.json()[0]["text"] == "secret page"


async def test_missing_key_returns_423(async_client, db_session):
    workspace_id = await _setup_workspace(async_client)
    session, token = await _session_and_token(async_client, db_session, workspace_id)
    key = b"k" * 32

    item = TaxItem(
        session_id=session.id,
        item_type="deduction",
        category="tools_equipment",
        amount=10,
        description=None,
        description_enc=encrypt_text("secret item", key),
        needs_review=False,
        review_status="confirmed",
    )
    db_session.add(item)
    await db_session.commit()

    clear_session_key(token)
    locked = await async_client.get(f"/api/workspaces/{workspace_id}/items")
    assert locked.status_code == 423


async def test_backfill_dry_run_does_not_mutate(async_client, db_session):
    workspace_id = await _setup_workspace(async_client)
    session, token = await _session_and_token(async_client, db_session, workspace_id)
    item = TaxItem(
        session_id=session.id,
        item_type="deduction",
        category="tools_equipment",
        amount=10,
        description="plain desc",
        needs_review=False,
        review_status="confirmed",
    )
    db_session.add(item)
    await db_session.commit()
    counts = await backfill_sensitive_fields(db_session, get_session_key(token), dry_run=True)
    assert counts["tax_item_description_encrypted"] >= 1
    row = await db_session.execute(select(TaxItem).where(TaxItem.id == item.id))
    item2 = row.scalar_one()
    assert item2.description_enc is None


async def test_backfill_encrypts_missing_fields(async_client, db_session):
    workspace_id = await _setup_workspace(async_client)
    session, token = await _session_and_token(async_client, db_session, workspace_id)
    item = TaxItem(
        session_id=session.id,
        item_type="deduction",
        category="tools_equipment",
        amount=10,
        description="plain desc",
        needs_review=False,
        review_status="confirmed",
    )
    db_session.add(item)
    await db_session.commit()
    counts = await backfill_sensitive_fields(db_session, get_session_key(token), dry_run=False)
    assert counts["tax_item_description_encrypted"] >= 1
    row = await db_session.execute(select(TaxItem).where(TaxItem.id == item.id))
    item2 = row.scalar_one()
    assert item2.description_enc is not None


async def test_legacy_plaintext_row_still_readable(async_client, db_session):
    workspace_id = await _setup_workspace(async_client)
    session, _token = await _session_and_token(async_client, db_session, workspace_id)
    item = TaxItem(
        session_id=session.id,
        item_type="deduction",
        category="tools_equipment",
        amount=10,
        description="legacy plain",
        needs_review=False,
        review_status="confirmed",
    )
    db_session.add(item)
    await db_session.commit()
    res = await async_client.get(f"/api/workspaces/{workspace_id}/items")
    assert res.status_code == 200
    assert any(i["description"] == "legacy plain" for i in res.json())


async def test_classification_write_blocked_without_key(db_session):
    settings.ai_provider = "mock"
    session = TaxSession(title="S", financial_year="2025-2026", status="draft")
    db_session.add(session)
    await db_session.flush()
    doc = Document(
        session_id=session.id,
        original_filename="x.pdf",
        mime_type="application/pdf",
        file_size_bytes=1,
        status="uploaded",
        financial_year="2025-2026",
    )
    db_session.add(doc)
    await db_session.commit()
    try:
        await classify_document(
            db=db_session,
            document_id=doc.id,
            session_id=session.id,
            extracted_text="salary 100",
            financial_year="2025-2026",
            skill_context="test",
        )
        assert False, "classification should be blocked without key"
    except EncryptionKeyUnavailableError:
        assert True


async def test_classification_writes_encrypted_only_with_key(async_client, db_session):
    settings.ai_provider = "mock"
    workspace_id = await _setup_workspace(async_client)
    session, token = await _session_and_token(async_client, db_session, workspace_id)
    key = get_session_key(token)
    assert key is not None
    doc = Document(
        session_id=session.id,
        original_filename="x.pdf",
        mime_type="application/pdf",
        file_size_bytes=1,
        status="uploaded",
        financial_year=session.financial_year,
    )
    db_session.add(doc)
    await db_session.commit()
    items = await classify_document(
        db=db_session,
        document_id=doc.id,
        session_id=session.id,
        extracted_text="salary 100",
        financial_year=session.financial_year,
        skill_context="test",
    )
    assert len(items) >= 1
    item_row = await db_session.execute(select(TaxItem).where(TaxItem.id == items[0].id))
    saved = item_row.scalar_one()
    assert saved.description is None
    assert saved.description_enc is not None
    cr_row = await db_session.execute(
        select(ClassificationResultModel).where(ClassificationResultModel.document_id == doc.id).order_by(ClassificationResultModel.created_at.desc())
    )
    cls = cr_row.scalars().first()
    assert cls is not None
    assert cls.raw_input is None
    assert cls.raw_input_enc is not None


async def test_ocr_write_blocked_without_key(db_session):
    session = TaxSession(title="S", financial_year="2025-2026", status="draft")
    db_session.add(session)
    await db_session.flush()
    doc = Document(
        session_id=session.id,
        original_filename="x.txt",
        mime_type="text/plain",
        file_size_bytes=8,
        status="uploaded",
        financial_year="2025-2026",
    )
    db_session.add(doc)
    await db_session.flush()
    job = Job(session_id=session.id, document_id=doc.id, job_type="ingestion", status="queued")
    db_session.add(job)
    await db_session.commit()
    try:
        await process_upload(
            db=db_session,
            document_id=doc.id,
            job_id=job.id,
            session_id=session.id,
            original_filename="x.txt",
            mime_type="text/plain",
            file_data=b"hello tax",
        )
        assert False, "ocr write should be blocked without key"
    except EncryptionKeyUnavailableError:
        assert True
    pages = await db_session.execute(select(DocumentPage).where(DocumentPage.document_id == doc.id))
    assert len(pages.scalars().all()) == 0


async def test_password_reset_keeps_encrypted_data_access(async_client, db_session):
    setup = await async_client.post("/api/auth/setup", json={"master_password": "supersecure123"})
    assert setup.status_code == 200
    recovery_key = setup.json()["recovery_key"]
    ws = await async_client.get("/api/workspaces")
    workspace_id = ws.json()[0]["id"]
    ensure = await async_client.get(f"/api/workspaces/{workspace_id}/items")
    assert ensure.status_code == 200
    row = await db_session.execute(select(TaxSession).where(TaxSession.workspace_id == workspace_id))
    session = row.scalar_one()
    token = async_client.cookies.get("taxai_session")
    key = get_session_key(token)
    assert key is not None

    item = TaxItem(
        session_id=session.id,
        item_type="deduction",
        category="tools_equipment",
        amount=10,
        description=None,
        description_enc=encrypt_text("stable secret", key),
        needs_review=False,
        review_status="confirmed",
    )
    db_session.add(item)
    await db_session.commit()

    reset = await async_client.post(
        "/api/auth/recover-reset",
        json={"recovery_key": recovery_key, "new_master_password": "newsecure123"},
    )
    assert reset.status_code == 200

    read = await async_client.get(f"/api/workspaces/{workspace_id}/items")
    assert read.status_code == 200
    assert any(i["description"] == "stable secret" for i in read.json())
