from datetime import datetime, timezone
import json
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, Form, Query, Request
from fastapi.responses import Response
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.deps import get_db
from app.db.auth_deps import get_current_user, get_current_unlocked_user
from app.services.auth.service import resolve_session
from app.db.workspace_scope import get_or_create_workspace_session, get_workspace_for_user, touch_workspace_opened
from app.models.document import Document
from app.models.document_page import DocumentPage
from app.models.export_package import ExportPackageModel
from app.models.tax_item import TaxItem
from app.models.user import User
from app.models.tax_workspace import TaxWorkspace
from app.models.audit_log import AuditLog
from app.models.classification_result import ClassificationResultModel
from app.models.document_item import DocumentItem
from app.schemas.workspace import WorkspaceCreateRequest, WorkspaceResponse
from app.schemas.document import DocumentPageResponse
from app.services.auth.service import seed_default_workspaces
from app.services.compliance_review import run_compliance_review
from app.services.export.encrypted_pack import generate_encrypted_review_pack
from app.services.export.encrypted_pack import validate_export_password
from app.schemas.tax_item import (
    WorkspaceReviewStatusUpdate,
    WorkspaceReviewSummaryResponse,
    TaxItemResponse,
    WorkspaceManualItemCreateRequest,
)
from app.schemas.export import WorkspaceExportGenerateRequest, WorkspaceExportRecord
from app.services.audit.writer import write_audit
from app.services.export.cleanup import cleanup_deleted_review_packs
from app.services.job import create_job, update_job_status
from app.services.security.key_cache import get_session_key
from app.services.security.field_encryption import decrypt_text, is_encrypted
from app.db.auth_deps import get_request_token
from app.services.security.unlock_capability import get_capability_metrics
from app.config import settings

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])
VALID_REVIEW_STATUSES = {"draft", "needs_review", "confirmed", "excluded", "tax_agent_review"}
SECURITY_EVENT_ACTIONS = {
    "workspace_locked",
    "workspace_unlocked",
    "auto_lock_triggered",
    "session_expired",
    "recovery_reset_completed",
    "invalid_session_token",
    "unlock_failed",
    "encryption_key_missing",
    "encrypted_write_blocked",
}


def _runtime_provider_mode() -> str:
    provider = (settings.ai_provider or "mock").lower()
    if provider == "mock":
        return "mock"
    if provider in {"openai", "anthropic"}:
        return "cloud"
    return "manual"


MANUAL_REVIEW_DOCUMENT_STATUSES = {"needs_review", "failed", "classification_failed", "extraction_failed"}


def _safe_audit_details(details: str | None) -> str | None:
    if not details:
        return details
    try:
        payload = json.loads(details)
    except Exception:
        return details
    if not isinstance(payload, dict):
        return details
    redacted = {}
    for key, value in payload.items():
        key_l = key.lower()
        if "text" in key_l or "ocr" in key_l or "content" in key_l:
            redacted[key] = "[redacted]"
        else:
            redacted[key] = value
    return json.dumps(redacted, separators=(",", ":"))


def _friendly_classification_reason(doc: Document) -> str | None:
    if doc.classification_status == "not_configured":
        return "Text extracted; AI classification needs setup/manual review."
    if doc.classification_status == "failed":
        return "Text extracted, but classification failed. Manual review required."
    if doc.extraction_status == "no_text":
        return "OCR returned no text."
    return doc.status_reason


def _to_response(ws: TaxWorkspace) -> WorkspaceResponse:
    return WorkspaceResponse(
        id=ws.id,
        user_id=ws.user_id,
        tax_year=ws.tax_year,
        label=ws.label,
        status=ws.status,
        created_at=ws.created_at.isoformat(),
        updated_at=ws.updated_at.isoformat(),
        last_opened_at=ws.last_opened_at.isoformat() if ws.last_opened_at else None,
    )


def _require_session_field_key(request: Request) -> bytes:
    token = get_request_token(request)
    key = get_session_key(token)
    if not key:
        raise HTTPException(status_code=423, detail="Workspace is locked. Unlock to view sensitive tax data.")
    return key


async def _require_field_key_for_write(
    db: AsyncSession,
    request: Request,
    entity_type: str,
    entity_id: str,
    field_names: list[str],
) -> bytes:
    key = get_session_key(get_request_token(request))
    if key:
        return key
    await write_audit(
        db,
        entity_type,
        entity_id,
        "encryption_key_missing",
        details={"stage": "write", "field_count": len(field_names)},
    )
    await write_audit(
        db,
        entity_type,
        entity_id,
        "encrypted_write_blocked",
        details={"fields": field_names},
    )
    await db.commit()
    raise HTTPException(status_code=423, detail="Workspace is locked. Unlock to view sensitive tax data.")


def _decrypt_item_fields(item: TaxItem, key: bytes) -> None:
    if item.description_enc:
        item.description = decrypt_text(item.description_enc, key)
    elif item.description and is_encrypted(item.description):
        item.description = decrypt_text(item.description, key)
    if getattr(item, "notes_enc", None):
        item.notes = decrypt_text(item.notes_enc, key)
    if getattr(item, "review_reason_enc", None):
        item.review_reason = decrypt_text(item.review_reason_enc, key)


async def _field_plaintext_stats(
    db: AsyncSession,
    model,
    plain_field: str,
    enc_field: str,
    session_id: str | None = None,
) -> dict:
    result = await db.execute(select(model))
    rows = result.scalars().all()
    if session_id is not None:
        rows = [r for r in rows if getattr(r, "session_id", None) == session_id]
    total = len(rows)
    plaintext_only = 0
    encrypted_only = 0
    mixed = 0
    neither = 0
    for row in rows:
        has_plain = bool(getattr(row, plain_field, None))
        has_enc = bool(getattr(row, enc_field, None))
        if has_plain and has_enc:
            mixed += 1
        elif has_plain and not has_enc:
            plaintext_only += 1
        elif has_enc and not has_plain:
            encrypted_only += 1
        else:
            neither += 1
    completion = 100.0 if total == 0 else round(((encrypted_only + mixed) / total) * 100.0, 2)
    return {
        "total_rows": total,
        "plaintext_only_rows": plaintext_only,
        "encrypted_rows": encrypted_only,
        "mixed_rows": mixed,
        "empty_rows": neither,
        "migration_completion_percent": completion,
    }


@router.get("", response_model=list[WorkspaceResponse])
async def list_workspaces(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await seed_default_workspaces(db, current_user.id)
    result = await db.execute(
        select(TaxWorkspace)
        .where(TaxWorkspace.user_id == current_user.id)
        .order_by(TaxWorkspace.tax_year.desc(), TaxWorkspace.created_at.desc())
    )
    workspaces = result.scalars().all()
    await db.commit()
    return [_to_response(ws) for ws in workspaces]


@router.post("", response_model=WorkspaceResponse)
async def create_workspace(
    payload: WorkspaceCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TaxWorkspace).where(
            TaxWorkspace.user_id == current_user.id,
            TaxWorkspace.tax_year == payload.tax_year,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Workspace for tax year already exists")

    ws = TaxWorkspace(
        user_id=current_user.id,
        tax_year=payload.tax_year,
        label=payload.label,
        status="active",
        last_opened_at=datetime.now(timezone.utc),
    )
    db.add(ws)
    await db.flush()
    await db.commit()
    await db.refresh(ws)
    return _to_response(ws)


@router.get("/{workspace_id}/documents")
async def list_workspace_documents(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_unlocked_user),
):
    workspace = await get_workspace_for_user(db, current_user, workspace_id)
    session = await get_or_create_workspace_session(db, workspace)
    await touch_workspace_opened(workspace)
    result = await db.execute(
        select(Document).where(Document.session_id == session.id).order_by(Document.created_at.desc())
    )
    docs = result.scalars().all()

    if not docs:
        await db.commit()
        return []

    doc_ids = [d.id for d in docs]
    item_counts_result = await db.execute(
        select(DocumentItem.document_id, func.count(DocumentItem.id))
        .where(DocumentItem.document_id.in_(doc_ids))
        .group_by(DocumentItem.document_id)
    )
    item_counts = {doc_id: count for doc_id, count in item_counts_result.all()}

    provider_rows = await db.execute(
        select(ClassificationResultModel.document_id, ClassificationResultModel.provider_name)
        .where(ClassificationResultModel.document_id.in_(doc_ids))
        .order_by(ClassificationResultModel.created_at.desc())
    )
    provider_mode_by_doc: dict[str, str] = {}
    for doc_id, provider_name in provider_rows.all():
        if doc_id in provider_mode_by_doc:
            continue
        provider_lower = (provider_name or "").lower()
        if "mock" in provider_lower:
            provider_mode_by_doc[doc_id] = "mock"
        elif "manual" in provider_lower:
            provider_mode_by_doc[doc_id] = "manual"
        elif "local" in provider_lower:
            provider_mode_by_doc[doc_id] = "local"
        else:
            provider_mode_by_doc[doc_id] = "cloud"

    payload = []
    for doc in docs:
        status_reason = doc.status_reason or ""
        retryable = False
        if doc.status in {"classification_failed", "extraction_failed", "failed"}:
            lower_reason = status_reason.lower()
            retryable = any(t in lower_reason for t in ["temporary", "timeout", "network", "unavailable", "try again"])
            if not status_reason:
                retryable = True
        provider_mode = provider_mode_by_doc.get(doc.id)
        if not provider_mode and doc.status == "needs_review":
            provider_mode = "manual"
        if not provider_mode:
            provider_mode = _runtime_provider_mode()
        payload.append(
            {
                "id": doc.id,
                "session_id": doc.session_id,
                "original_filename": doc.original_filename,
                "mime_type": doc.mime_type,
                "file_size_bytes": doc.file_size_bytes,
                "file_hash": doc.file_hash,
                "category": doc.category,
                "financial_year": doc.financial_year,
                "status": doc.status,
                "status_reason": _friendly_classification_reason(doc),
                "created_at": doc.created_at,
                "updated_at": doc.updated_at,
                "item_count": item_counts.get(doc.id, 0),
                "provider_mode": provider_mode,
                "retryable": retryable,
                "extraction_status": doc.extraction_status or ("no_text" if doc.status == "needs_review" and item_counts.get(doc.id, 0) == 0 else "pending"),
                "extraction_text_length": doc.extraction_text_length or 0,
                "classification_status": doc.classification_status or ("classified" if doc.status == "classified" else "pending"),
                "classification_provider": doc.classification_provider or provider_mode_by_doc.get(doc.id),
                "classification_error": doc.classification_error,
            }
        )
    await db.commit()
    return payload


@router.post("/{workspace_id}/documents/upload", status_code=202)
async def upload_workspace_document(
    workspace_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    category: str | None = Form(default=None),
    financial_year: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_unlocked_user),
):
    # Reuse existing upload behavior and OCR/classification pipeline unchanged.
    from app.routers.documents import upload_document

    workspace = await get_workspace_for_user(db, current_user, workspace_id)
    session = await get_or_create_workspace_session(db, workspace)
    await touch_workspace_opened(workspace)
    capability_token = get_request_token(request)
    _u, auth_session = await resolve_session(db, capability_token)

    return await upload_document(
        background_tasks=background_tasks,
        session_id=session.id,
        file=file,
        category=category,
        financial_year=financial_year or session.financial_year,
        workspace_id=workspace_id,
        owner_user_id=current_user.id,
        capability_token=capability_token,
        capability_expires_at=auth_session.expires_at if auth_session else None,
        db=db,
        current_user=current_user,
    )


@router.get("/{workspace_id}/items", response_model=list[TaxItemResponse])
async def list_workspace_items(
    workspace_id: str,
    review_status: str | None = Query(default=None),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_unlocked_user),
):
    if review_status and review_status not in VALID_REVIEW_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid review_status filter")
    workspace = await get_workspace_for_user(db, current_user, workspace_id)
    session = await get_or_create_workspace_session(db, workspace)
    await touch_workspace_opened(workspace)
    stmt = select(TaxItem).where(TaxItem.session_id == session.id).order_by(TaxItem.created_at.desc())
    if review_status:
        stmt = stmt.where(TaxItem.review_status == review_status)
    result = await db.execute(stmt)
    items = result.scalars().all()
    legacy_plaintext_reads = 0
    if any(i.description_enc or i.review_reason_enc or getattr(i, "notes_enc", None) for i in items):
        key = _require_session_field_key(request)
        for item in items:
            _decrypt_item_fields(item, key)
    for item in items:
        if not item.description_enc and item.description:
            legacy_plaintext_reads += 1
        if not getattr(item, "notes_enc", None) and getattr(item, "notes", None):
            legacy_plaintext_reads += 1
        if not item.review_reason_enc and item.review_reason:
            legacy_plaintext_reads += 1
    if legacy_plaintext_reads > 0:
        await write_audit(
            db,
            "tax_workspace",
            workspace_id,
            "plaintext_legacy_read",
            details={"entity": "tax_item", "field_reads": legacy_plaintext_reads},
        )
    await db.commit()
    return items


@router.patch("/{workspace_id}/items/{item_id}/review-status")
async def set_workspace_item_review_status(
    workspace_id: str,
    item_id: str,
    payload: WorkspaceReviewStatusUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_unlocked_user),
):
    if payload.review_status not in {"needs_review", "confirmed", "excluded", "tax_agent_review"}:
        raise HTTPException(status_code=400, detail="Invalid review_status")

    workspace = await get_workspace_for_user(db, current_user, workspace_id)
    session = await get_or_create_workspace_session(db, workspace)
    await touch_workspace_opened(workspace)

    result = await db.execute(
        select(TaxItem).where(TaxItem.id == item_id, TaxItem.session_id == session.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    previous_status = item.review_status
    item.review_status = payload.review_status
    item.needs_review = payload.review_status in {"draft", "needs_review", "tax_agent_review"}
    key = await _require_field_key_for_write(
        db,
        request,
        "tax_item",
        item.id,
        ["review_reason"],
    )
    item.review_reason = None
    item.review_reason_enc = None
    if payload.note:
        from app.services.security.field_encryption import encrypt_text, ENCRYPTION_VERSION, DEFAULT_KEY_VERSION

        item.review_reason_enc = encrypt_text(payload.note, key)
        item.encryption_version = ENCRYPTION_VERSION
        item.key_version = DEFAULT_KEY_VERSION
    item.reviewed_at = datetime.now(timezone.utc)
    item.reviewed_by = "user"

    await write_audit(
        db,
        "tax_item",
        item.id,
        "review_status_updated",
        details={
            "from_status": previous_status,
            "to_status": payload.review_status,
            "has_note": bool(payload.note),
        },
    )
    await db.flush()
    await db.commit()
    await db.refresh(item)
    _decrypt_item_fields(item, key)
    return item


@router.get("/{workspace_id}/documents/{document_id}/pages", response_model=list[DocumentPageResponse])
async def list_workspace_document_pages(
    workspace_id: str,
    document_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_unlocked_user),
):
    workspace = await get_workspace_for_user(db, current_user, workspace_id)
    session = await get_or_create_workspace_session(db, workspace)
    await touch_workspace_opened(workspace)
    doc_result = await db.execute(
        select(Document).where(Document.id == document_id, Document.session_id == session.id)
    )
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    page_result = await db.execute(
        select(DocumentPage).where(DocumentPage.document_id == document_id).order_by(DocumentPage.page_number.asc())
    )
    pages = page_result.scalars().all()
    legacy_plaintext_reads = 0
    if any((p.text_enc or (p.text and is_encrypted(p.text))) for p in pages):
        key = _require_session_field_key(request)
        for page in pages:
            if page.text_enc:
                page.text = decrypt_text(page.text_enc, key)
            elif page.text and is_encrypted(page.text):
                page.text = decrypt_text(page.text, key)
    for page in pages:
        if not page.text_enc and page.text:
            legacy_plaintext_reads += 1
    if legacy_plaintext_reads > 0:
        await write_audit(
            db,
            "tax_workspace",
            workspace_id,
            "plaintext_legacy_read",
            details={"entity": "document_page", "field_reads": legacy_plaintext_reads},
        )
    await db.commit()
    return pages


@router.get("/{workspace_id}/review-summary", response_model=WorkspaceReviewSummaryResponse)
async def workspace_review_summary(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_unlocked_user),
):
    workspace = await get_workspace_for_user(db, current_user, workspace_id)
    session = await get_or_create_workspace_session(db, workspace)
    await touch_workspace_opened(workspace)
    result = await db.execute(select(TaxItem).where(TaxItem.session_id == session.id))
    items = result.scalars().all()
    doc_result = await db.execute(select(Document).where(Document.session_id == session.id))
    docs = doc_result.scalars().all()
    unresolved_manual_review_documents = []
    for doc in docs:
        if doc.status not in MANUAL_REVIEW_DOCUMENT_STATUSES:
            continue
        count_result = await db.execute(
            select(func.count(DocumentItem.id)).where(DocumentItem.document_id == doc.id)
        )
        doc_item_count = int(count_result.scalar_one() or 0)
        if doc_item_count == 0:
            unresolved_manual_review_documents.append(doc)

    counts = {status: 0 for status in VALID_REVIEW_STATUSES}
    for item in items:
        status = item.review_status if item.review_status in counts else ("needs_review" if item.needs_review else "confirmed")
        counts[status] += 1

    blocking_reasons: list[str] = []
    if len(items) == 0:
        blocking_reasons.append("No review items available yet.")
    if counts["draft"] > 0:
        blocking_reasons.append(f"{counts['draft']} item(s) are still in draft.")
    if counts["needs_review"] > 0:
        blocking_reasons.append(f"{counts['needs_review']} item(s) still need review.")
    if counts["tax_agent_review"] > 0:
        blocking_reasons.append(f"{counts['tax_agent_review']} item(s) require tax agent review.")
    if len(unresolved_manual_review_documents) > 0:
        blocking_reasons.append(
            f"{len(unresolved_manual_review_documents)} document(s) need manual review before export."
        )

    return WorkspaceReviewSummaryResponse(
        total_items=len(items),
        draft=counts["draft"],
        needs_review=counts["needs_review"],
        confirmed=counts["confirmed"],
        excluded=counts["excluded"],
        tax_agent_review=counts["tax_agent_review"],
        manual_review_documents=len(unresolved_manual_review_documents),
        ready_for_export=len(blocking_reasons) == 0,
        blocking_reasons=blocking_reasons,
    )


@router.get("/{workspace_id}/manual-review-documents")
async def list_workspace_manual_review_documents(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_unlocked_user),
):
    workspace = await get_workspace_for_user(db, current_user, workspace_id)
    session = await get_or_create_workspace_session(db, workspace)
    await touch_workspace_opened(workspace)
    doc_result = await db.execute(
        select(Document).where(Document.session_id == session.id).order_by(Document.created_at.desc())
    )
    docs = doc_result.scalars().all()
    payload: list[dict] = []
    for doc in docs:
        if doc.status not in MANUAL_REVIEW_DOCUMENT_STATUSES:
            continue
        count_result = await db.execute(
            select(func.count(DocumentItem.id)).where(DocumentItem.document_id == doc.id)
        )
        item_count = int(count_result.scalar_one() or 0)
        if item_count > 0:
            continue
        payload.append(
            {
                "id": doc.id,
                "filename": doc.original_filename,
                "status": doc.status,
                "status_reason": doc.status_reason,
                "provider_mode": "manual" if doc.status == "needs_review" else _runtime_provider_mode(),
                "item_count": item_count,
                "created_at": doc.created_at,
            }
        )
    await db.commit()
    return payload


@router.post("/{workspace_id}/documents/{document_id}/manual-item", response_model=TaxItemResponse)
async def create_workspace_manual_item(
    workspace_id: str,
    document_id: str,
    payload: WorkspaceManualItemCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_unlocked_user),
):
    workspace = await get_workspace_for_user(db, current_user, workspace_id)
    session = await get_or_create_workspace_session(db, workspace)
    await touch_workspace_opened(workspace)
    doc_result = await db.execute(
        select(Document).where(Document.id == document_id, Document.session_id == session.id)
    )
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    review_status = payload.review_status if payload.review_status in VALID_REVIEW_STATUSES else "needs_review"
    key = await _require_field_key_for_write(
        db,
        request,
        "tax_item",
        document_id,
        ["description", "review_reason"],
    )
    from app.services.security.field_encryption import encrypt_text, ENCRYPTION_VERSION, DEFAULT_KEY_VERSION

    item = TaxItem(
        session_id=session.id,
        item_type=payload.item_type or "needs_review",
        category=payload.category or "needs_review",
        amount=payload.amount,
        description=None,
        description_enc=encrypt_text(payload.description, key),
        confidence=0.0,
        needs_review=review_status in {"draft", "needs_review", "tax_agent_review"},
        review_status=review_status,
        review_reason=None,
        review_reason_enc=encrypt_text(payload.note, key) if payload.note else None,
        reviewed_by="user",
        encryption_version=ENCRYPTION_VERSION,
        key_version=DEFAULT_KEY_VERSION,
    )
    db.add(item)
    await db.flush()
    db.add(DocumentItem(document_id=doc.id, tax_item_id=item.id))
    if doc.status in MANUAL_REVIEW_DOCUMENT_STATUSES:
        doc.status = "reviewed"
        doc.status_reason = "Manual item added by user."
    await write_audit(
        db,
        "tax_item",
        item.id,
        "manual_item_created",
        details={"workspace_id": workspace_id, "document_id": doc.id, "review_status": review_status},
    )
    await db.commit()
    await db.refresh(item)
    _decrypt_item_fields(item, key)
    return item


@router.post("/{workspace_id}/documents/{document_id}/manual-review-action")
async def apply_workspace_manual_review_action(
    workspace_id: str,
    document_id: str,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_unlocked_user),
):
    action = str(payload.get("action") or "").strip().lower()
    if action not in {"exclude_document", "tax_agent_review"}:
        raise HTTPException(status_code=400, detail="Invalid manual review action")
    workspace = await get_workspace_for_user(db, current_user, workspace_id)
    session = await get_or_create_workspace_session(db, workspace)
    await touch_workspace_opened(workspace)
    doc_result = await db.execute(
        select(Document).where(Document.id == document_id, Document.session_id == session.id)
    )
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if action == "exclude_document":
        doc.status = "reviewed"
        doc.status_reason = "Excluded by user from review pack."
        audit_action = "manual_review_document_excluded"
    else:
        doc.status = "needs_review"
        doc.status_reason = "Marked for tax agent review."
        audit_action = "manual_review_document_tax_agent_review"
    await write_audit(
        db,
        "document",
        doc.id,
        audit_action,
        details={"workspace_id": workspace_id},
    )
    await db.commit()
    return {"ok": True}


@router.get("/{workspace_id}/issues")
async def list_workspace_issues(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_unlocked_user),
):
    workspace = await get_workspace_for_user(db, current_user, workspace_id)
    session = await get_or_create_workspace_session(db, workspace)
    await touch_workspace_opened(workspace)
    return await run_compliance_review(db, session.id)


@router.post("/{workspace_id}/review-pack")
async def generate_workspace_review_pack(
    workspace_id: str,
    format: str = Query("json", pattern="^(json|csv)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    raise HTTPException(
        status_code=410,
        detail="Legacy workspace review-pack route disabled. Use /api/workspaces/{workspace_id}/review-pack/generate.",
    )


@router.post("/{workspace_id}/review-pack/generate", response_model=WorkspaceExportRecord)
async def generate_workspace_encrypted_review_pack(
    workspace_id: str,
    payload: WorkspaceExportGenerateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_unlocked_user),
):
    pw_error = validate_export_password(payload.export_password)
    if pw_error:
        raise HTTPException(status_code=400, detail=pw_error)

    summary = await workspace_review_summary(workspace_id, db=db, current_user=current_user)
    if not summary.ready_for_export:
        raise HTTPException(status_code=409, detail=f"Review pack is blocked: {summary.blocking_reasons}")

    workspace = await get_workspace_for_user(db, current_user, workspace_id)
    session = await get_or_create_workspace_session(db, workspace)
    await touch_workspace_opened(workspace)
    capability_token = get_request_token(request)
    _u, auth_session = await resolve_session(db, capability_token)
    export_job = await create_job(
        db=db,
        session_id=session.id,
        document_id=None,
        job_type="export",
        workspace_id=workspace_id,
        user_id=current_user.id,
        requires_encryption=True,
        capability_token=capability_token,
        capability_expires_at=auth_session.expires_at if auth_session else None,
        payload={"stage": "review_pack_generation"},
    )
    await update_job_status(db, export_job["id"], "running", progress=0.2, progress_message="Preparing encrypted review pack")
    await db.commit()

    try:
        record = await generate_encrypted_review_pack(
            db=db,
            workspace_id=workspace_id,
            session_id=session.id,
            export_password=payload.export_password,
            include_source_documents=payload.include_source_documents,
            blocking_reasons=summary.blocking_reasons,
        )
    except ValueError as exc:
        await update_job_status(db, export_job["id"], "failed", error_message="Export generation blocked")
        await db.commit()
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        await update_job_status(db, export_job["id"], "failed", error_message="Export generation failed")
        await db.commit()
        raise

    await write_audit(
        db,
        "export_package",
        record.id,
        "encrypted_review_pack_generated",
        details={"workspace_id": workspace_id, "export_id": record.id, "encrypted": True, "job_id": export_job["id"]},
    )
    await update_job_status(db, export_job["id"], "succeeded", progress=1.0, progress_message="Encrypted review pack generated", result_summary=f'{{"export_id":"{record.id}"}}')
    await db.commit()
    await db.refresh(record)
    return record


@router.get("/{workspace_id}/review-pack", response_model=list[WorkspaceExportRecord])
async def list_workspace_review_pack_history(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_unlocked_user),
):
    workspace = await get_workspace_for_user(db, current_user, workspace_id)
    await touch_workspace_opened(workspace)
    result = await db.execute(
        select(ExportPackageModel)
        .where(
            ExportPackageModel.workspace_id == workspace_id,
            ExportPackageModel.status != "deleted",
            ExportPackageModel.storage_path.is_not(None),
        )
        .order_by(ExportPackageModel.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{workspace_id}/review-pack/{export_id}/download")
async def download_workspace_review_pack(
    workspace_id: str,
    export_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_unlocked_user),
):
    workspace = await get_workspace_for_user(db, current_user, workspace_id)
    await touch_workspace_opened(workspace)
    result = await db.execute(
        select(ExportPackageModel).where(
            ExportPackageModel.id == export_id,
            ExportPackageModel.workspace_id == workspace_id,
        )
    )
    record = result.scalar_one_or_none()
    if not record or not record.storage_path:
        raise HTTPException(status_code=404, detail="Export package not found")

    from pathlib import Path

    path = Path(record.storage_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Export file not found")

    record.downloaded_at = datetime.now(timezone.utc)
    await write_audit(
        db,
        "export_package",
        record.id,
        "review_pack_downloaded",
        details={"workspace_id": workspace_id, "export_id": record.id},
    )
    await db.flush()
    await db.commit()
    return Response(
        content=path.read_bytes(),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={record.filename or path.name}"},
    )


@router.delete("/{workspace_id}/review-pack/{export_id}")
async def delete_workspace_review_pack(
    workspace_id: str,
    export_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_unlocked_user),
):
    workspace = await get_workspace_for_user(db, current_user, workspace_id)
    await touch_workspace_opened(workspace)
    result = await db.execute(
        select(ExportPackageModel).where(
            ExportPackageModel.id == export_id,
            ExportPackageModel.workspace_id == workspace_id,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Export package not found")

    if record.storage_path:
        from pathlib import Path
        path = Path(record.storage_path)
        if path.exists():
            path.unlink()

    record.status = "deleted"
    record.storage_path = None
    await write_audit(
        db,
        "export_package",
        record.id,
        "review_pack_deleted",
        details={"workspace_id": workspace_id, "export_id": record.id},
    )
    await db.flush()
    await db.commit()
    return {"ok": True}


@router.post("/{workspace_id}/review-pack/cleanup")
async def cleanup_workspace_review_pack_files(
    workspace_id: str,
    older_than_days: int | None = Query(default=None, ge=0, le=3650),
    include_ready_exports: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_unlocked_user),
):
    await get_workspace_for_user(db, current_user, workspace_id)
    result = await cleanup_deleted_review_packs(
        db,
        older_than_days=older_than_days,
        include_ready_exports=include_ready_exports,
    )
    await write_audit(
        db,
        "workspace",
        workspace_id,
        "review_pack_cleanup_run",
        details={
            "older_than_days": older_than_days,
            "include_ready_exports": include_ready_exports,
            "deleted_file_count": result.deleted_file_count,
            "marked_deleted_count": result.marked_deleted_count,
        },
    )
    await db.commit()
    return {
        "deleted_file_count": result.deleted_file_count,
        "skipped_missing_file_count": result.skipped_missing_file_count,
        "marked_deleted_count": result.marked_deleted_count,
    }


@router.get("/{workspace_id}/security/status")
async def workspace_security_status(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_unlocked_user),
):
    workspace = await get_workspace_for_user(db, current_user, workspace_id)
    session = await get_or_create_workspace_session(db, workspace)
    await touch_workspace_opened(workspace)

    doc_stats = await _field_plaintext_stats(db, DocumentPage, "text", "text_enc")
    item_desc = await _field_plaintext_stats(db, TaxItem, "description", "description_enc", session_id=session.id)
    class_in = await _field_plaintext_stats(db, ClassificationResultModel, "raw_input", "raw_input_enc", session_id=session.id)
    class_out = await _field_plaintext_stats(db, ClassificationResultModel, "raw_output", "raw_output_enc", session_id=session.id)
    classification_stats = {
        "total_rows": class_in["total_rows"],
        "plaintext_only_rows": class_in["plaintext_only_rows"] + class_out["plaintext_only_rows"],
        "encrypted_rows": class_in["encrypted_rows"] + class_out["encrypted_rows"],
        "mixed_rows": class_in["mixed_rows"] + class_out["mixed_rows"],
        "migration_completion_percent": round(
            (class_in["migration_completion_percent"] + class_out["migration_completion_percent"]) / 2.0, 2
        ),
    }
    table_completion = [
        doc_stats["migration_completion_percent"],
        item_desc["migration_completion_percent"],
        classification_stats["migration_completion_percent"],
    ]
    overall_completion = round(sum(table_completion) / len(table_completion), 2)
    blocking_tables = []
    if doc_stats["plaintext_only_rows"] > 0:
        blocking_tables.append("document_pages")
    if item_desc["plaintext_only_rows"] > 0:
        blocking_tables.append("tax_items")
    if classification_stats["plaintext_only_rows"] > 0:
        blocking_tables.append("classification_results")

    audit_summary = await db.execute(
        select(AuditLog.action).where(
            AuditLog.action.in_(["encrypted_write_blocked", "unlock_failed", "workspace_locked", "workspace_unlocked"])
        )
    )
    actions = [row[0] for row in audit_summary.all()]
    recent_sec_events = await db.execute(
        select(AuditLog)
        .where(AuditLog.action.in_(list(SECURITY_EVENT_ACTIONS)))
        .order_by(AuditLog.created_at.desc())
        .limit(12)
    )
    recent = recent_sec_events.scalars().all()
    return {
        "encryption_enabled": "field_level_partial",
        "export_encryption_enabled": True,
        "session_status": "UNLOCKED",
        "recovery_key_configured": bool(current_user.recovery_key_hash),
        "last_unlock_at": current_user.last_unlocked_at.isoformat() if current_user.last_unlocked_at else None,
        "plaintext_readiness": {
            "document_pages": doc_stats,
            "tax_items": item_desc,
            "classification_results": classification_stats,
            "overall_migration_completion_percent": overall_completion,
        },
        "migration_readiness": {
            "can_disable_plaintext_fallback": len(blocking_tables) == 0,
            "blocking_tables": blocking_tables,
            "legacy_read_paths": [
                "workspaces.list_workspace_items",
                "workspaces.list_workspace_document_pages",
                "classification_results legacy plaintext fallback",
            ],
        },
        "operational_visibility": {
            "backup_status": "manual_runbook",
            "locked_write_counter": actions.count("encrypted_write_blocked"),
            "failed_unlock_counter": actions.count("unlock_failed"),
            "capability_metrics": get_capability_metrics(),
        },
        "recent_security_events": [
            {
                "action": row.action,
                "created_at": row.created_at,
                "entity_type": row.entity_type,
            }
            for row in recent
        ],
    }


@router.get("/{workspace_id}/audit-events")
async def list_workspace_audit_events(
    workspace_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_unlocked_user),
):
    workspace = await get_workspace_for_user(db, current_user, workspace_id)
    session = await get_or_create_workspace_session(db, workspace)
    await touch_workspace_opened(workspace)

    docs_result = await db.execute(select(Document.id).where(Document.session_id == session.id))
    document_ids = [row[0] for row in docs_result.all()]
    items_result = await db.execute(select(TaxItem.id).where(TaxItem.session_id == session.id))
    item_ids = [row[0] for row in items_result.all()]
    exports_result = await db.execute(select(ExportPackageModel.id).where(ExportPackageModel.workspace_id == workspace_id))
    export_ids = [row[0] for row in exports_result.all()]

    filters = [(AuditLog.entity_type == "workspace") & (AuditLog.entity_id == workspace_id)]
    filters.append((AuditLog.entity_type == "tax_session") & (AuditLog.entity_id == session.id))
    if document_ids:
        filters.append((AuditLog.entity_type == "document") & (AuditLog.entity_id.in_(document_ids)))
    if item_ids:
        filters.append((AuditLog.entity_type == "tax_item") & (AuditLog.entity_id.in_(item_ids)))
    if export_ids:
        filters.append((AuditLog.entity_type == "export_package") & (AuditLog.entity_id.in_(export_ids)))

    result = await db.execute(
        select(AuditLog)
        .where(or_(*filters))
        .order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = result.scalars().all()
    return [
        {
            "id": row.id,
            "entity_type": row.entity_type,
            "entity_id": row.entity_id,
            "action": row.action,
            "changed_by": row.changed_by,
            "details": _safe_audit_details(row.details),
            "created_at": row.created_at,
        }
        for row in rows
    ]
