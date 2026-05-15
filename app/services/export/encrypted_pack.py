import csv
import io
import json
import hashlib
import secrets
import base64
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.document import Document
from app.models.export_package import ExportPackageModel
from app.models.tax_item import TaxItem
from app.models.tax_session import TaxSession

PACK_VERSION = "1.0"
APP_NAME = "Tax Return AI"
WEAK_PASSWORDS = {
    "password",
    "password123",
    "123456789012",
    "qwerty123456",
    "letmein123456",
}


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8")


def _derive_key(password: str, salt: bytes) -> tuple[str, bytes, dict]:
    try:
        from argon2.low_level import hash_secret_raw, Type

        key = hash_secret_raw(
            secret=password.encode("utf-8"),
            salt=salt,
            time_cost=3,
            memory_cost=65536,
            parallelism=2,
            hash_len=32,
            type=Type.ID,
        )
        return "argon2id", key, {"time_cost": 3, "memory_cost": 65536, "parallelism": 2}
    except Exception:
        key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 600_000, dklen=32)
        return "pbkdf2_sha256_600k", key, {"iterations": 600000}


def validate_export_password(password: str) -> str | None:
    if password is None:
        return "Export password is required."
    if password.strip() == "":
        return "Export password cannot be empty."
    if len(password) < 12:
        return "Export password must be at least 12 characters."
    if password.lower() in WEAK_PASSWORDS:
        return "Export password is too common. Choose a stronger password."
    return None


def _encrypt_bytes(plaintext: bytes, password: str) -> tuple[bytes, str, dict]:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    salt = secrets.token_bytes(16)
    nonce = secrets.token_bytes(12)
    kdf, key, kdf_params = _derive_key(password, salt)
    aes = AESGCM(key)
    ciphertext = aes.encrypt(nonce, plaintext, None)

    envelope = {
        "version": PACK_VERSION,
        "alg": "AES-256-GCM",
        "kdf": kdf,
        "kdf_params": kdf_params,
        "salt": _b64(salt),
        "nonce": _b64(nonce),
    }
    header = (json.dumps(envelope, separators=(",", ":")) + "\n").encode("utf-8")
    return header + ciphertext, kdf, envelope


def _build_evidence_index_csv(items: list[TaxItem], docs_by_id: dict[str, Document]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["item_id", "category", "amount", "source_document_id", "source_document_name", "status", "confidence", "reviewer_note"])
    for item in items:
        writer.writerow([
            item.id,
            item.category,
            item.amount if item.amount is not None else "",
            "",
            "",
            item.review_status,
            item.confidence if item.confidence is not None else "",
            item.review_reason or "",
        ])
    output.seek(0)
    return output.getvalue()


def _export_dir() -> Path:
    base = Path(getattr(settings, "storage_local_path", "./data/uploads")).resolve().parent
    path = base / "exports"
    path.mkdir(parents=True, exist_ok=True)
    return path


async def generate_encrypted_review_pack(
    db: AsyncSession,
    workspace_id: str,
    session_id: str,
    export_password: str,
    include_source_documents: bool,
    blocking_reasons: list[str],
) -> ExportPackageModel:
    if include_source_documents:
        raise ValueError("include_source_documents is not supported in this MVP")

    s_row = await db.execute(select(TaxSession).where(TaxSession.id == session_id))
    session = s_row.scalar_one_or_none()
    if not session:
        raise ValueError("Session not found")

    d_row = await db.execute(select(Document).where(Document.session_id == session_id))
    documents = d_row.scalars().all()
    docs_by_id = {d.id: d for d in documents}

    i_row = await db.execute(select(TaxItem).where(TaxItem.session_id == session_id))
    items = i_row.scalars().all()

    confirmed = [i for i in items if i.review_status == "confirmed"]
    excluded = [i for i in items if i.review_status == "excluded"]
    tax_agent_review = [i for i in items if i.review_status == "tax_agent_review"]

    generated_at = datetime.now(timezone.utc).isoformat()
    report = {
        "workspace_id": workspace_id,
        "session_id": session_id,
        "financial_year": session.financial_year,
        "generated_at": generated_at,
        "summary": {
            "total_items": len(items),
            "confirmed": len(confirmed),
            "excluded": len(excluded),
            "tax_agent_review": len(tax_agent_review),
            "document_count": len(documents),
        },
        "confirmed_items": [
            {"id": i.id, "category": i.category, "amount": i.amount, "description": i.description}
            for i in confirmed
        ],
        "excluded_items_summary": {"count": len(excluded)},
        "tax_agent_review_items_summary": {"count": len(tax_agent_review)},
        "blocking_reasons_snapshot": blocking_reasons,
        "disclaimer": "This review pack is prepared for human review and is not a final tax return or lodgement.",
    }

    extracted = {
        "workspace_id": workspace_id,
        "session_id": session_id,
        "items": [
            {
                "id": i.id,
                "item_type": i.item_type,
                "category": i.category,
                "amount": i.amount,
                "description": i.description,
                "confidence": i.confidence,
                "review_status": i.review_status,
                "review_reason": i.review_reason,
            }
            for i in items
        ],
    }

    evidence_csv = _build_evidence_index_csv(items, docs_by_id)

    content_manifest = {
        "files": [
            "review-report.json",
            "extracted-items.json",
            "evidence-index.csv",
            "metadata.json",
        ]
    }

    mem_zip = io.BytesIO()
    with ZipFile(mem_zip, "w", compression=ZIP_DEFLATED) as zf:
        zf.writestr("review-report.json", json.dumps(report, separators=(",", ":"), ensure_ascii=True))
        zf.writestr("extracted-items.json", json.dumps(extracted, separators=(",", ":"), ensure_ascii=True))
        zf.writestr("evidence-index.csv", evidence_csv)
        # metadata filled after encryption metadata is known; temp placeholder.
        zf.writestr("metadata.json", json.dumps({"pending": True}))

    zip_bytes = mem_zip.getvalue()
    plaintext_manifest_sha256 = hashlib.sha256(zip_bytes).hexdigest()

    encrypted_bytes, kdf, envelope = _encrypt_bytes(zip_bytes, export_password)

    metadata = {
        "app": APP_NAME,
        "export_format_version": PACK_VERSION,
        "encryption": {
            "alg": envelope["alg"],
            "kdf": envelope["kdf"],
            "kdf_params": envelope["kdf_params"],
            "salt": envelope["salt"],
            "nonce": envelope["nonce"],
        },
        "generated_at": generated_at,
        "plaintext_manifest_sha256": plaintext_manifest_sha256,
        "package_contents": content_manifest["files"],
    }

    # Rebuild zip with final metadata so metadata.json is present in plaintext package before encryption.
    mem_zip2 = io.BytesIO()
    with ZipFile(mem_zip2, "w", compression=ZIP_DEFLATED) as zf:
        zf.writestr("review-report.json", json.dumps(report, separators=(",", ":"), ensure_ascii=True))
        zf.writestr("extracted-items.json", json.dumps(extracted, separators=(",", ":"), ensure_ascii=True))
        zf.writestr("evidence-index.csv", evidence_csv)
        zf.writestr("metadata.json", json.dumps(metadata, separators=(",", ":"), ensure_ascii=True))
    zip_bytes_final = mem_zip2.getvalue()
    encrypted_bytes, kdf, envelope = _encrypt_bytes(zip_bytes_final, export_password)

    out_dir = _export_dir()
    export_id = secrets.token_hex(8)
    filename = f"tax-review-pack-{export_id}.enc.zip"
    path = out_dir / filename
    path.write_bytes(encrypted_bytes)

    file_sha = hashlib.sha256(encrypted_bytes).hexdigest()
    file_size = path.stat().st_size

    record = ExportPackageModel(
        session_id=session_id,
        workspace_id=workspace_id,
        filename=filename,
        status="ready",
        format="enc_zip_v1",
        encrypted=True,
        kdf=kdf,
        encryption_version=PACK_VERSION,
        kdf_params_summary=json.dumps(envelope.get("kdf_params", {}), separators=(",", ":")),
        file_size=file_size,
        sha256=file_sha,
        item_count=len(items),
        document_count=len(documents),
        blocking_reasons=json.dumps(blocking_reasons),
        storage_path=str(path),
        export_data=None,
        exported_by="user",
    )
    db.add(record)
    await db.flush()
    return record
