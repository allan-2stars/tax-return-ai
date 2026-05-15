"""Shared test fixtures."""
import pytest
from app.ai.providers.mock import MockProvider
from app.ocr.providers.mock import MockOCRProvider


@pytest.fixture
def mock_ai_provider():
    return MockProvider()


@pytest.fixture
def mock_ocr_provider():
    return MockOCRProvider()
