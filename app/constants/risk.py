"""Risk and status enums. Single source of truth — must match JSON schemas."""
from enum import StrEnum


class RiskLevel(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"


class ReviewStatus(StrEnum):
    """Canonical values used by tax_items, classification_results, and compliance_review."""
    auto_classified = "auto_classified"
    needs_user_review = "needs_user_review"
    needs_tax_agent_review = "needs_tax_agent_review"
    user_confirmed = "user_confirmed"
    excluded_by_user = "excluded_by_user"
    ready_for_export = "ready_for_export"


class EvidenceStatus(StrEnum):
    complete = "complete"
    partial = "partial"
    missing_or_incomplete = "missing_or_incomplete"
    not_required = "not_required"


class JobStatus(StrEnum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"
    retrying = "retrying"


class TaxSessionStatus(StrEnum):
    draft = "draft"
    importing = "importing"
    reviewing = "reviewing"
    ready_for_export = "ready_for_export"
    exported = "exported"
    archived = "archived"


class DocumentStatus(StrEnum):
    uploaded = "uploaded"
    stored = "stored"
    text_extracted = "text_extracted"
    ocr_required = "ocr_required"
    ocr_completed = "ocr_completed"
    extraction_failed = "extraction_failed"
    normalised = "normalised"
    duplicate_detected = "duplicate_detected"
    ready_for_classification = "ready_for_classification"
    classified = "classified"
    classification_failed = "classification_failed"
    needs_review = "needs_review"
    reviewed = "reviewed"
    exported = "exported"
