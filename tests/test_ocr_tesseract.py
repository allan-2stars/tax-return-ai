"""Tests for Tesseract OCR extraction.

These are unit tests for the TesseractProvider error handling and result shapes.
Real OCR requires tesseract binaries installed (they are, via Dockerfile).
"""
import pytest
from app.ocr.providers.base import OCRResult


class TestTesseractProvider:
    """Tests for TesseractProvider — focuses on error handling and edge cases."""

    @pytest.fixture
    def provider(self):
        from app.ocr.providers.tesseract import TesseractProvider
        return TesseractProvider()

    async def test_empty_bytes_returns_empty_result(self, provider):
        """Empty bytes should return a graceful fallback."""
        result = await provider.extract(b"", "image/png")
        assert isinstance(result, OCRResult)
        assert len(result.pages) == 1

    async def test_not_an_image_handles_gracefully(self, provider):
        """Random bytes shouldn't crash."""
        result = await provider.extract(b"not an image", "image/png")
        assert isinstance(result, OCRResult)

    async def test_result_shape(self, provider):
        """OCRResult should always have pages and method."""
        result = await provider.extract(b"", "image/png")
        assert hasattr(result, "pages")
        assert hasattr(result, "method")
        assert hasattr(result, "full_text")
