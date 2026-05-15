"""Verify AI adapter contract — mock provider returns schema-valid output."""
import asyncio
import json
from pathlib import Path
from jsonschema import Draft202012Validator
from app.ai.providers.mock import MockProvider


def test_mock_provider_health():
    result = asyncio.get_event_loop().run_until_complete(MockProvider().health_check())
    assert result is True


def test_mock_provider_output_is_schema_valid():
    provider = MockProvider()
    schema = json.loads(
        Path("skills/tax-return-specialist/schemas/tax_analysis_output.schema.json").read_text()
    )
    result_list = asyncio.get_event_loop().run_until_complete(
        provider.classify("sample text", "doc_test", "2025-2026", "")
    )
    errors = []
    for i, result in enumerate(result_list):
        item_errors = list(Draft202012Validator(schema).iter_errors(result))
        for e in item_errors:
            e.message = f"[item {i}] {e.message}"
        errors.extend(item_errors)
    assert not errors, [e.message for e in errors]
