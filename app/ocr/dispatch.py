"""Smart OCR dispatch — picks the right provider by document mime_type.

Mime type → provider mapping:
  - application/pdf → pdfplumber (with tesseract fallback for image-only PDFs)
  - image/png, image/jpeg, image/tiff, image/webp → tesseract
  - text/plain → identity (no OCR needed)
  - text/csv, application/json → identity

For PDFs, if pdfplumber returns empty text (image-only scan),
falls back to tesseract for full-page OCR.
"""
from app.ocr.providers.base import OCRResult, OCRPage
from app.config import settings


# ── Mime type categories ─────────────────────────────────────────────────────
_PDF_MIMES = {"application/pdf"}
_IMAGE_MIMES = {"image/png", "image/jpeg", "image/jpg", "image/tiff", "image/webp", "image/bmp"}
_TEXT_MIMES = {"text/plain", "text/csv", "text/html", "application/json", "application/xml"}
_PASS_THROUGH_MIMES = _TEXT_MIMES | {"application/octet-stream"}


def _get_provider(provider_name: str):
    """Lazy-import and instantiate an OCR provider by name."""
    if provider_name == "pdfplumber":
        from app.ocr.providers.pdfplumber import PdfPlumberProvider
        return PdfPlumberProvider()
    if provider_name == "tesseract":
        from app.ocr.providers.tesseract import TesseractProvider
        return TesseractProvider()
    if provider_name == "mock":
        from app.ocr.providers.mock import MockOCRProvider
        return MockOCRProvider()
    raise ValueError(f"Unknown OCR provider: {provider_name}")


async def extract_text(data: bytes, mime_type: str) -> OCRResult:
    """Extract text from document bytes using the best provider for this mime type.

    For PDFs: try pdfplumber first, fall back to tesseract if result is empty.
    For images: use tesseract directly.
    For text: return the raw bytes as a single-page OCRResult.
    """
    mime_lower = mime_type.lower().split(";")[0].strip()

    # Pass-through for plain text
    if mime_lower in _PASS_THROUGH_MIMES:
        text = data.decode("utf-8", errors="replace")
        return OCRResult(
            pages=[OCRPage(page_number=1, text=text, confidence=1.0)],
            method="identity",
        )

    # PDFs: pdfplumber → fallback tesseract
    if mime_lower in _PDF_MIMES:
        provider = _get_provider("pdfplumber")
        result = await provider.extract(data, mime_type)

        # If pdfplumber returned empty text, fall back to tesseract
        if not result.full_text.strip():
            tesseract_provider = _get_provider("tesseract")
            fallback = await tesseract_provider.extract(data, mime_type)
            if fallback.full_text.strip():
                return OCRResult(
                    pages=fallback.pages,
                    method=f"pdfplumber_fallback_tesseract",
                )

        return result

    # Images: tesseract directly
    if mime_lower in _IMAGE_MIMES:
        provider = _get_provider("tesseract")
        return await provider.extract(data, mime_type)

    # Unknown type — try tesseract, then mock
    tesseract_provider = _get_provider("tesseract")
    result = await tesseract_provider.extract(data, mime_type)
    if result.full_text.strip():
        return result

    return OCRResult(
        pages=[OCRPage(page_number=1, text="", confidence=0.0)],
        method=f"unsupported_type:{mime_type}",
    )
