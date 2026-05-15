"""Tests for PDF OCR extraction using pdfplumber.

These are unit tests for the parsing logic, not full integration tests.
They test the error-handling paths without needing a real PDF file.
"""
import pytest
from app.ocr.providers.base import OCRResult, OCRPage


class TestPdfPlumberProvider:
    """Tests for PdfPlumberProvider — focuses on error handling and edge cases."""

    @pytest.fixture
    def provider(self):
        from app.ocr.providers.pdfplumber import PdfPlumberProvider
        return PdfPlumberProvider()

    async def test_empty_bytes_returns_empty_result(self, provider):
        """Empty PDF bytes should return empty text with 0.0 confidence."""
        result = await provider.extract(b"", "application/pdf")
        assert isinstance(result, OCRResult)
        assert len(result.pages) == 1
        assert result.pages[0].text == ""
        assert result.pages[0].confidence == 0.0

    async def test_not_a_pdf_handles_gracefully(self, provider):
        """Random bytes should not crash — returns graceful fallback."""
        result = await provider.extract(b"not a real pdf content whatsoever", "application/pdf")
        # pdfplumber won't open this, so it'll catch the exception
        assert isinstance(result, OCRResult)

    async def test_result_has_full_text_property(self, provider):
        """OCRResult.full_text should join all pages."""
        result = OCRResult(
            pages=[
                OCRPage(page_number=1, text="Page one text.", confidence=0.9),
                OCRPage(page_number=2, text="Page two text.", confidence=0.85),
            ],
            method="pdfplumber",
        )
        assert "Page one text." in result.full_text
        assert "Page two text." in result.full_text

    async def test_single_page_result(self, provider):
        """Single page result should work."""
        result = OCRResult(
            pages=[OCRPage(page_number=1, text="Single page", confidence=0.95)],
            method="pdfplumber",
        )
        assert result.full_text == "Single page"
        assert result.method == "pdfplumber"
