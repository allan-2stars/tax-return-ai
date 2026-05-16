"""Classification service — orchestrates AI provider calls for document classification.

Wraps the AI provider interface and:
- Sends document text to configured AI provider
- Enforces needs_review=true when confidence < 0.7
- Writes audit events
- Creates tax_item records from classification results
- Stores DocumentItem links to source documents
- Logs raw classification results to the classification_results table
"""
import asyncio
import json
import time as time_module
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.ai.factory import get_provider
from app.ai.providers.base import (
    ClassificationResult,
    AIProviderConfigurationError,
)
from app.models.tax_item import TaxItem
from app.models.document_item import DocumentItem
from app.models.classification_result import ClassificationResultModel
from app.services.audit.writer import write_audit
from app.models.tax_session import TaxSession
from app.models.tax_workspace import TaxWorkspace
from app.services.security.key_cache import get_user_active_key
from app.services.security.field_encryption import (
    encrypt_text,
    ENCRYPTION_VERSION,
    DEFAULT_KEY_VERSION,
    EncryptionKeyUnavailableError,
)


CONFIDENCE_REVIEW_THRESHOLD = 0.7

RETRYABLE_EXCEPTIONS = (TimeoutError, ConnectionError, ConnectionResetError)
PROVIDER_NOT_CONFIGURED_MESSAGE = "AI classification is not configured. Document needs manual review."


async def classify_document(
    db: AsyncSession,
    document_id: str,
    session_id: str,
    extracted_text: str,
    financial_year: str,
    skill_context: str = "",
) -> list[TaxItem]:
    """
    Classify extracted document text using the configured AI provider.

    Returns a list of created TaxItems — one per detected line/item in the document —
    with review flags set appropriately.
    """
    provider = get_provider()
    provider_name = type(provider).__name__.replace("Provider", "").lower()
    field_key = await _get_session_field_key(db, session_id)
    if not field_key:
        await write_audit(
            db,
            "classification_result",
            document_id,
            "encryption_key_missing",
            details={"stage": "classification_write", "session_id": session_id},
        )
        await write_audit(
            db,
            "classification_result",
            document_id,
            "encrypted_write_blocked",
            details={"fields": ["raw_input", "raw_output", "tax_item.description", "tax_item.review_reason"]},
        )
        await db.commit()
        raise EncryptionKeyUnavailableError("Workspace encryption key unavailable")

    # Call AI provider with timing (with retry for transient errors)
    start_time = time_module.monotonic()
    max_attempts = 2
    try:
        for attempt in range(1, max_attempts + 1):
            try:
                results = await provider.classify(
                    extracted_text=extracted_text,
                    document_id=document_id,
                    financial_year=financial_year,
                    skill_context=skill_context,
                )
                break  # success — exit retry loop
            except RETRYABLE_EXCEPTIONS:
                if attempt < max_attempts:
                    await asyncio.sleep(2)
                    continue  # retry
                # Last attempt failed — fall through to outer catch
                raise
    except AIProviderConfigurationError as exc:
        processing_time_ms = round((time_module.monotonic() - start_time) * 1000)
        failed_result = ClassificationResultModel(
            document_id=document_id,
            session_id=session_id,
            provider_name=provider_name,
            raw_input=None,
            raw_input_enc=encrypt_text(extracted_text, field_key),
            raw_output=None,
            parsed_output=None,
            confidence=None,
            processing_time_ms=processing_time_ms,
            success=False,
            error_message=PROVIDER_NOT_CONFIGURED_MESSAGE,
            model_version=None,
        )
        db.add(failed_result)
        await db.flush()
        await write_audit(
            db, "classification_result", failed_result.id, "provider_not_configured",
            details={
                "document_id": document_id,
                "provider": provider_name,
                "processing_time_ms": processing_time_ms,
            },
        )
        await db.commit()
        raise
    except Exception as exc:
        # Save failed classification result
        processing_time_ms = round((time_module.monotonic() - start_time) * 1000)
        failed_result = ClassificationResultModel(
            document_id=document_id,
            session_id=session_id,
            provider_name=provider_name,
            raw_input=extracted_text,
            raw_output=None,
            parsed_output=None,
            confidence=None,
            processing_time_ms=processing_time_ms,
            success=False,
            error_message=str(exc),
            model_version=None,
        )
        db.add(failed_result)
        await db.flush()
        await write_audit(
            db, "classification_result", failed_result.id, "failed",
            details={
                "document_id": document_id,
                "provider": provider_name,
                "error": str(exc),
                "processing_time_ms": processing_time_ms,
            },
        )
        await db.commit()
        raise

    processing_time_ms = round((time_module.monotonic() - start_time) * 1000)

    # Enforce review rules on each result
    results = [_apply_review_rules(r) for r in results]

    # Save classification result record (one record per classification call)
    model_version = (
        results[0].get("metadata", {}).get("model_version")
        if results and isinstance(results[0].get("metadata"), dict)
        else None
    )
    classification_record = ClassificationResultModel(
        document_id=document_id,
        session_id=session_id,
        provider_name=provider_name,
        raw_input=None,
        raw_input_enc=encrypt_text(extracted_text, field_key),
        raw_output=None,
        raw_output_enc=encrypt_text(json.dumps([dict(r) for r in results]), field_key),
        encryption_version=ENCRYPTION_VERSION,
        key_version=DEFAULT_KEY_VERSION,
        parsed_output=json.dumps([dict(r) for r in results]),
        confidence=results[0].get("confidence") if results else None,
        processing_time_ms=processing_time_ms,
        success=True,
        error_message=None,
        model_version=model_version,
    )
    db.add(classification_record)
    await db.flush()

    # Create tax items — one per classification result
    items: list[TaxItem] = []
    for result in results:
        item = TaxItem(
            session_id=session_id,
            item_type=result.get("item_type", "needs_review"),
            category=result.get("category", "needs_review"),
            amount=result.get("amount"),
            description=None,
            description_enc=encrypt_text(result.get("description", "Classified by AI"), field_key),
            confidence=result.get("confidence", 0.0),
            needs_review=result.get("needs_review", True),
            review_reason=None,
            review_reason_enc=encrypt_text(result.get("review_reason"), field_key),
            encryption_version=ENCRYPTION_VERSION,
            key_version=DEFAULT_KEY_VERSION,
            ato_reference_hint=result.get("ato_reference_hint"),
        )
        db.add(item)
        await db.flush()

        # Link each item to the source document
        link = DocumentItem(
            document_id=document_id,
            tax_item_id=item.id,
            snippet=extracted_text[:500] if extracted_text else None,
        )
        db.add(link)
        await db.flush()

        items.append(item)

    # Write audit — log items (plural) count
    await write_audit(
        db, "tax_item", ",".join(str(i.id) for i in items), "classified",
        details={
            "document_id": document_id,
            "provider": provider_name,
            "item_count": len(items),
            "categories": [r.get("category") for r in results],
            "confidences": [r.get("confidence") for r in results],
            "needs_review": any(r.get("needs_review") for r in results),
        },
    )

    await db.commit()
    for item in items:
        await db.refresh(item)
    return items


def _apply_review_rules(result: ClassificationResult) -> ClassificationResult:
    """Enforce classification rules:
    - If confidence < 0.7, needs_review must be True
    - If needs_review is True, review_reason must be set
    """
    confidence = result.get("confidence", 0.0)

    if confidence < CONFIDENCE_REVIEW_THRESHOLD:
        result["needs_review"] = True
        if not result.get("review_reason"):
            result["review_reason"] = (
                f"Low confidence ({confidence:.0%}). "
                f"Requires human review before use."
            )

    if result.get("needs_review") and not result.get("review_reason"):
        result["review_reason"] = "Requires human review."

    return result


async def _get_session_field_key(db: AsyncSession, session_id: str) -> bytes | None:
    result = await db.execute(
        select(TaxWorkspace.user_id)
        .join(TaxSession, TaxSession.workspace_id == TaxWorkspace.id)
        .where(TaxSession.id == session_id)
    )
    user_id = result.scalar_one_or_none()
    if not user_id:
        return None
    return get_user_active_key(user_id)
