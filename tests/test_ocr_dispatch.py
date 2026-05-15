"""Tests for the OCR dispatch layer — mime-type routing and fallback logic."""
import pytest
from app.ocr.dispatch import extract_text
from app.ocr.providers.base import OCRResult


class TestOCRDispatch:
    """Tests for the mime-type based OCR dispatcher."""

    async def test_text_plain_passthrough(self):
        """Plain text should pass through without OCR."""
        result = await extract_text(b"Hello, this is a tax receipt.", "text/plain")
        assert result.method == "identity"
        assert "Hello, this is a tax receipt." in result.full_text
        assert result.pages[0].confidence == 1.0

    async def test_csv_passthrough(self):
        """CSV content should pass through without OCR."""
        content = "date,amount,description\n2025-07-01,100.0,Sale"
        result = await extract_text(content.encode(), "text/csv")
        assert result.method == "identity"
        assert "2025-07-01" in result.full_text

    async def test_json_passthrough(self):
        """JSON content passes through."""
        result = await extract_text(b'{"key": "value"}', "application/json")
        assert result.method == "identity"

    async def test_unknown_mime_falls_back(self):
        """Unknown mime types should attempt tesseract and fall back gracefully."""
        result = await extract_text(b"some random binary data", "application/octet-stream")
        assert isinstance(result, OCRResult)

    async def test_pdf_empty_bytes(self):
        """Empty PDF bytes handled gracefully."""
        result = await extract_text(b"", "application/pdf")
        assert isinstance(result, OCRResult)

    async def test_image_empty_bytes(self):
        """Empty image bytes handled gracefully."""
        result = await extract_text(b"", "image/png")
        assert isinstance(result, OCRResult)

    async def test_result_always_has_method(self):
        """Every OCRResult should report which method was used."""
        result = await extract_text(b"test data", "text/plain")
        assert result.method is not None
        assert len(result.method) > 0

    async def test_mime_case_insensitive(self):
        """Mime types should be handled case-insensitively."""
        result = await extract_text(b"plain text", "TEXT/PLAIN")
        assert result.method == "identity"

    async def test_mime_with_charset(self):
        """Mime types with charset parameters should work."""
        result = await extract_text(b"hello", "text/plain; charset=utf-8")
        assert result.method == "identity"
