"""Tests for Anthropic and OpenAI provider parsing/fallback logic.

These test the JSON parsing and error-handling logic without needing API keys.
The actual API calls are integration tests and require ANTHROPIC_API_KEY / OPENAI_API_KEY.
"""
import json
import sys

sys.path.insert(0, ".")

# Test shared provider utilities (used by both anthropic.py and openai.py)
from app.ai.providers.shared import (
    parse_json_response,
    build_classification_result,
    _infer_ato_reference,
)

# Test MockProvider
from app.ai.providers.mock import MockProvider
from app.services.classification import classify_document
from app.models.tax_session import TaxSession
from app.models.document import Document


# ── MockProvider direct tests ──────────────────────────────────────────────


async def test_mock_provider_direct():
    """MockProvider.classify() returns a list of ClassificationResult dicts
    with the expected keys and sensible values for a salary text."""
    provider = MockProvider()
    results = await provider.classify(
        extracted_text="Salary from employer: $85,000",
        document_id="test-doc-1",
        financial_year="2025-2026",
        skill_context="",
    )

    # It should be a list
    assert isinstance(results, list), "classify() should return a list"

    # Each element should be a dict (ClassificationResult)
    for result in results:
        assert isinstance(result, dict)

    # Must contain the required keys in each element
    required_keys = {"item_type", "category", "confidence", "needs_review"}
    for result in results:
        assert required_keys.issubset(result.keys()), (
            f"Missing keys: {required_keys - set(result.keys())}"
        )

    # At least one result should map "salary" text to item_type "income"
    income_results = [r for r in results if r["item_type"] == "income"]
    assert len(income_results) >= 1, (
        f"Expected at least one 'income' result, got item_types: {[r['item_type'] for r in results]}"
    )

    # confidence must be a float between 0 and 1 for all results
    for result in results:
        assert isinstance(result["confidence"], float), (
            f"confidence should be float, got {type(result['confidence'])}"
        )
        assert 0.0 <= result["confidence"] <= 1.0, (
            f"confidence {result['confidence']} outside [0, 1]"
        )


async def test_mock_provider_empty_text():
    """MockProvider.classify() with empty text returns
    a list with a single result with needs_review=True and low confidence."""
    provider = MockProvider()
    results = await provider.classify(
        extracted_text="",
        document_id="test-doc-empty",
        financial_year="2025-2026",
        skill_context="",
    )

    assert isinstance(results, list), "classify() should return a list"
    assert len(results) == 1, "Empty text should return exactly one result"
    result = results[0]
    assert isinstance(result, dict)
    assert result["needs_review"] is True, "Empty text should always require review"
    assert result["confidence"] < 0.5, (
        f"Expected low confidence for empty text, got {result['confidence']}"
    )
    assert result["item_type"] == "needs_review"
    assert result["category"] == "insufficient_evidence"
    assert result["review_reason"] is not None


# ── MockProvider via service ────────────────────────────────────────────────


async def test_mock_provider_via_service(db_session):
    """classify_document() creates a TaxItem persisted in the database."""
    # 1. Create a tax session and a document
    session = TaxSession(
        title="Test Session",
        financial_year="2025-2026",
    )
    db_session.add(session)
    await db_session.flush()

    doc = Document(
        session_id=session.id,
        original_filename="test_salary.pdf",
        mime_type="application/pdf",
        file_size_bytes=1024,
        status="text_extracted",
    )
    db_session.add(doc)
    await db_session.flush()

    # 2. Call classify_document with the real session and document
    extracted_text = "Salary from employer: $85,000"
    items = await classify_document(
        db=db_session,
        document_id=doc.id,
        session_id=session.id,
        extracted_text=extracted_text,
        financial_year="2025-2026",
    )

    # 3. Verify we got a list with one TaxItem
    assert isinstance(items, list), "classify_document should return a list"
    assert len(items) >= 1, "Should have at least one TaxItem"
    item = items[0]
    assert item.session_id == session.id
    assert item.item_type == "income"
    assert item.category == "salary_wages"
    assert item.confidence == 0.95
    assert item.needs_review is False

    # 4. Verify it's persisted — query it back
    from sqlalchemy import select

    query = select(type(item)).where(type(item).id == item.id)
    result = await db_session.execute(query)
    fetched = result.scalar_one_or_none()
    assert fetched is not None, "TaxItem was not persisted in the database"
    assert fetched.id == item.id
    assert fetched.session_id == session.id
    assert fetched.item_type == "income"
    assert fetched.category == "salary_wages"


# ── Shared JSON parse tests ────────────────────────────────────────────────


def test_parse_direct_json():
    """Plain JSON should parse directly."""
    raw = '{"item_type": "income", "category": "salary_wages", "confidence": 0.95, "description": "Salary", "risk_level": "low", "review_status": "auto_classified", "reasoning_summary": "Clear salary document."}'
    parsed = parse_json_response(raw)
    assert parsed is not None
    assert parsed["item_type"] == "income"
    assert parsed["category"] == "salary_wages"
    print("  ✓ test_parse_direct_json")


def test_parse_code_block():
    """JSON wrapped in ```json ... ``` should be extracted."""
    raw = """Here is the classification result:
```json
{
    "item_type": "deduction",
    "category": "tools_equipment",
    "confidence": 0.70,
    "description": "USB hub and keyboard for WFH",
    "risk_level": "medium",
    "review_status": "needs_user_review",
    "reasoning_summary": "Work-use percentage not confirmed."
}
```"""
    parsed = parse_json_response(raw)
    assert parsed is not None
    assert parsed["item_type"] == "deduction"
    assert parsed["category"] == "tools_equipment"
    print("  ✓ test_parse_code_block")


def test_parse_extra_text():
    """JSON embedded in extra text should be extracted."""
    raw = 'Based on the document, here is my analysis:\n\n{"item_type": "deduction", "category": "donation", "confidence": 0.85, "description": "Charitable donation", "risk_level": "low", "review_status": "auto_classified", "reasoning_summary": "Clear charity receipt."}\n\nPlease review and confirm.'
    parsed = parse_json_response(raw)
    assert parsed is not None
    assert parsed["category"] == "donation"
    assert parsed["confidence"] == 0.85
    print("  ✓ test_parse_extra_text")


def test_parse_invalid():
    """Non-JSON response should return None."""
    parsed = parse_json_response("I cannot classify this document.")
    assert parsed is None
    print("  ✓ test_parse_invalid")


# ── Shared ClassificationResult builder tests ──────────────────────────────


def test_build_classification_result_anthropic():
    """Mapping with anthropic provider name."""
    sample = {
        "item_type": "income",
        "category": "salary_wages",
        "amount": 85000.0,
        "description": "Annual salary from ABC Corp.",
        "confidence": 0.95,
        "risk_level": "low",
        "review_status": "auto_classified",
        "reasoning_summary": "Clear PAYG payment summary.",
        "missing_fields": [],
        "suggested_user_questions": [],
        "supplier_or_source": "ABC Corp",
        "evidence_status": "complete",
        "audit": {
            "analysis_timestamp": "2025-07-01T10:00:00",
            "analysis_method": "ai",
            "model_version": "claude-3-haiku-20240307",
        },
    }
    result = build_classification_result(
        sample, "doc-1", "2025-2026",
        provider_name="anthropic",
        default_description="Classified by Anthropic.",
    )
    assert result["item_type"] == "income"
    assert result["category"] == "salary_wages"
    assert result["amount"] == 85000.0
    assert result["confidence"] == 0.95
    assert result["needs_review"] is False
    assert result["metadata"]["provider"] == "anthropic"
    print("  ✓ test_build_classification_result_anthropic")


def test_build_classification_result_review_trigger():
    """needs_user_review status maps to needs_review=True."""
    sample = {
        "item_type": "deduction",
        "category": "tools_equipment",
        "amount": 149.0,
        "description": "USB hub and keyboard.",
        "confidence": 0.68,
        "risk_level": "medium",
        "review_status": "needs_user_review",
        "reasoning_summary": "Work-use percentage not confirmed.",
        "missing_fields": ["work_use_percentage"],
        "suggested_user_questions": ["Is this 100% work-related?"],
    }
    result = build_classification_result(
        sample, "doc-2", "2025-2026",
        provider_name="anthropic",
        default_description="Classified by Anthropic.",
    )
    assert result["needs_review"] is True
    assert "Work-use percentage" in (result["review_reason"] or "")
    print("  ✓ test_build_classification_result_review_trigger")


def test_build_classification_result_openai():
    """Mapping with openai provider name."""
    sample = {
        "item_type": "deduction",
        "category": "union_fee",
        "amount": 450.0,
        "description": "Annual union membership.",
        "confidence": 0.92,
        "risk_level": "low",
        "review_status": "auto_classified",
        "reasoning_summary": "Standard union fee deduction.",
        "missing_fields": [],
        "suggested_user_questions": [],
    }
    result = build_classification_result(
        sample, "doc-3", "2025-2026",
        provider_name="openai",
        default_description="Classified by OpenAI.",
    )
    assert result["item_type"] == "deduction"
    assert result["category"] == "union_fee"
    assert result["confidence"] == 0.92
    assert result["needs_review"] is False
    assert result["metadata"]["provider"] == "openai"
    print("  ✓ test_build_classification_result_openai")


# ── ATO reference tests ────────────────────────────────────────────────────


def test_infer_ato_reference():
    """ATO reference hints map correctly."""
    assert _infer_ato_reference("salary_wages") == "Salary/Wages"
    assert _infer_ato_reference("work_from_home") == "D5"
    assert _infer_ato_reference("tools_equipment") == "D5"
    assert _infer_ato_reference("bank_interest") == "Interest"
    assert _infer_ato_reference("unknown_category") is None
    print("  ✓ test_infer_ato_reference")


if __name__ == "__main__":
    test_parse_direct_json()
    test_parse_code_block()
    test_parse_extra_text()
    test_parse_invalid()
    test_build_classification_result_anthropic()
    test_build_classification_result_review_trigger()
    test_build_classification_result_openai()
    test_infer_ato_reference()
    print()
    print("ALL PARSE/FALLBACK TESTS PASSED")
