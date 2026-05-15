"""OCR provider ABC."""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class OCRPage:
    page_number: int
    text: str
    confidence: float | None


@dataclass
class OCRResult:
    pages: list[OCRPage]
    method: str

    @property
    def full_text(self) -> str:
        return "\n\n".join(p.text for p in self.pages)


class OCRProvider(ABC):
    @abstractmethod
    async def extract(self, data: bytes, mime_type: str) -> OCRResult:
        """Extract text from document bytes."""
