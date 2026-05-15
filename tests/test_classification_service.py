"""Tests for the classification service.

Covers:
  - _apply_review_rules: confidence thresholds, review triggers
  - classify_document: orchestrates AI call, creates TaxItem via DB
"""
import pytest
from app.services.classification import (
    _apply_review_rules,
    classify_document,
    CONFIDENCE_REVIEW_THRESHOLD,
)


class TestApplyReviewRules:
    """Pure logic tests — no DB or AI calls needed."""

    def test_high_confidence_no_review_needed(self):
        result = _apply_review_rules({
            "item_type": "income",
            "category": "salary_wages",
            "confidence": 0.95,
            "needs_review": False,
        })
        assert result["needs_review"] is False

    def test_low_confidence_triggers_review(self):
        result = _apply_review_rules({
            "item_type": "deduction",
            "category": "tools_equipment",
            "confidence": 0.6,
            "needs_review": False,
        })
        assert result["needs_review"] is True
        assert "confidence" in result["review_reason"].lower()

    def test_boundary_confidence_just_below(self):
        """Confidence just below 0.7 should trigger review."""
        result = _apply_review_rules({
            "item_type": "income",
            "category": "bank_interest",
            "confidence": CONFIDENCE_REVIEW_THRESHOLD - 0.01,
            "needs_review": False,
        })
        assert result["needs_review"] is True

    def test_boundary_confidence_at_threshold(self):
        """Confidence exactly at 0.7 should NOT trigger review (not less than)."""
        result = _apply_review_rules({
            "item_type": "income",
            "category": "dividend",
            "confidence": CONFIDENCE_REVIEW_THRESHOLD,
            "needs_review": False,
        })
        assert result["needs_review"] is False

    def test_missing_confidence_defaults_to_zero(self):
        """Missing confidence should default to 0.0, triggering review."""
        result = _apply_review_rules({
            "item_type": "deduction",
            "category": "other",
        })
        assert result["needs_review"] is True
        assert result["confidence"] == 0.0

    def test_review_reason_set_when_missing(self):
        """If needs_review is True but no reason, should auto-set one."""
        result = _apply_review_rules({
            "item_type": "deduction",
            "category": "work_from_home",
            "confidence": 0.5,
            "needs_review": True,
            "review_reason": None,
        })
        assert result["needs_review"] is True
        assert result["review_reason"] is not None

    def test_existing_review_reason_preserved(self):
        """If a reason was already provided by the AI, keep it."""
        result = _apply_review_rules({
            "item_type": "deduction",
            "category": "mixed_use",
            "confidence": 0.6,
            "needs_review": True,
            "review_reason": "Mixed use — personal percentage not confirmed.",
        })
        assert result["review_reason"] == "Mixed use — personal percentage not confirmed."

    def test_item_type_defaults_to_needs_review_when_missing(self):
        result = _apply_review_rules({
            "category": "unknown",
            "confidence": 0.3,
            "needs_review": True,
            "review_reason": None,
        })
        assert result["needs_review"] is True
