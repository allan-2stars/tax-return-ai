"""Mock OCR provider for tests."""
from app.ocr.providers.base import OCRProvider, OCRPage, OCRResult


class MockOCRProvider(OCRProvider):
    async def extract(self, data: bytes, mime_type: str) -> OCRResult:
        return OCRResult(
            pages=[OCRPage(page_number=1, text="[mock extracted text]", confidence=1.0)],
            method="mock",
        )
