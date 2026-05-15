"""Return the configured OCR provider."""
from app.ocr.providers.base import OCRProvider
from app.config import settings


def get_ocr_provider() -> OCRProvider:
    provider = settings.ocr_provider.lower()
    if provider == "pdfplumber":
        from app.ocr.providers.pdfplumber import PdfPlumberProvider
        return PdfPlumberProvider()
    if provider == "tesseract":
        from app.ocr.providers.tesseract import TesseractProvider
        return TesseractProvider()
    if provider == "mock":
        from app.ocr.providers.mock import MockOCRProvider
        return MockOCRProvider()
    raise ValueError(f"Unknown OCR_PROVIDER: {provider!r}")
