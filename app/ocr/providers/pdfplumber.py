"""PDF text extraction using pdfplumber.

Extracts text from PDF documents page by page. Falls back gracefully
if pdfplumber is not installed or the PDF is image-only (returns empty pages).
"""
import io
from app.ocr.providers.base import OCRProvider, OCRPage, OCRResult


class PdfPlumberProvider(OCRProvider):
    """Extract text from PDF files using pdfplumber."""

    async def extract(self, data: bytes, mime_type: str) -> OCRResult:
        """Extract text from PDF bytes.

        Each page becomes an OCRPage with page_number and extracted text.
        Confidence is estimated from the ratio of extracted characters to
        raw file size — image-heavy PDFs score lower.
        """
        try:
            import pdfplumber
        except ImportError:
            return OCRResult(
                pages=[OCRPage(page_number=1, text="", confidence=0.0)],
                method="pdfplumber",
            )

        try:
            pages: list[OCRPage] = []
            with pdfplumber.open(io.BytesIO(data)) as pdf:
                for i, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text() or ""
                    char_count = len(text.strip())

                    # Confidence: more extracted text = higher confidence
                    # 0-100 chars → low, 100-500 → medium, 500+ → high
                    if char_count > 500:
                        confidence = 0.95
                    elif char_count > 100:
                        confidence = 0.75
                    elif char_count > 0:
                        confidence = 0.50
                    else:
                        confidence = 0.0

                    pages.append(OCRPage(
                        page_number=i,
                        text=text,
                        confidence=confidence,
                    ))

            if not pages:
                pages.append(OCRPage(
                    page_number=1,
                    text="",
                    confidence=0.0,
                ))

            return OCRResult(pages=pages, method="pdfplumber")

        except Exception as e:
            return OCRResult(
                pages=[OCRPage(page_number=1, text="", confidence=0.0)],
                method=f"pdfplumber_error: {e}",
            )
