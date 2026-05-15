"""Document Pydantic schemas."""
from datetime import datetime
from pydantic import BaseModel


class DocumentCreate(BaseModel):
    session_id: str
    original_filename: str
    mime_type: str
    file_size_bytes: int
    file_hash: str | None = None
    category: str | None = None
    financial_year: str | None = None


class DocumentUpdate(BaseModel):
    status: str | None = None
    status_reason: str | None = None
    category: str | None = None
    file_hash: str | None = None
    extracted_text_hash: str | None = None
    financial_year: str | None = None


class DocumentResponse(BaseModel):
    id: str
    session_id: str
    original_filename: str
    mime_type: str
    file_size_bytes: int
    file_hash: str | None
    storage_path: str | None
    extracted_text_hash: str | None
    status: str
    status_reason: str | None
    category: str | None
    financial_year: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentPageResponse(BaseModel):
    """Per-page OCR result for a document."""
    id: str
    document_id: str
    page_number: int
    text: str | None
    confidence: float | None
    ocr_method: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentUploadResponse(BaseModel):
    """Response from the file upload endpoint."""
    document: DocumentResponse
    duplicate_detected: bool
    duplicate_of: str | None
    pipeline_status: str
