"""Validate all skill schemas against their example files."""
import json
from pathlib import Path
import pytest
from jsonschema import Draft202012Validator

SCHEMA_EXAMPLES = [
    (
        "skills/tax-return-specialist/schemas/tax_analysis_output.schema.json",
        "skills/tax-return-specialist/examples/example-analysis-output.json",
    ),
    (
        "skills/tax-document-ingestion/schemas/document_ingestion.schema.json",
        "skills/tax-document-ingestion/templates/ingestion_result.example.json",
    ),
    (
        "skills/tax-compliance-review/schemas/compliance_review.schema.json",
        "skills/tax-compliance-review/examples/compliance_review.example.json",
    ),
]


@pytest.mark.parametrize("schema_path,example_path", SCHEMA_EXAMPLES)
def test_example_validates(schema_path, example_path):
    schema = json.loads(Path(schema_path).read_text())
    data = json.loads(Path(example_path).read_text())
    validator = Draft202012Validator(schema)
    items = data.get("items", [data]) if isinstance(data, dict) else data
    for item in items:
        errors = list(validator.iter_errors(item))
        assert not errors, f"{example_path}: {[e.message for e in errors]}"


def test_provider_swap_mock_returns_valid_schema(mock_ai_provider):
    """Mock provider must return schema-valid output without touching real APIs."""
    import asyncio
    result_list = asyncio.get_event_loop().run_until_complete(
        mock_ai_provider.classify("test text", "doc_001", "2025-2026", "")
    )
    schema = json.loads(
        Path("skills/tax-return-specialist/schemas/tax_analysis_output.schema.json").read_text()
    )
    validator = Draft202012Validator(schema)
    errors = []
    for i, result in enumerate(result_list):
        item_errors = list(validator.iter_errors(result))
        for e in item_errors:
            e.message = f"[item {i}] {e.message}"
        errors.extend(item_errors)
    assert not errors, f"Mock provider output invalid: {[e.message for e in errors]}"
