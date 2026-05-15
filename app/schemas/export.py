"""Export package Pydantic schemas."""
from datetime import datetime
from pydantic import BaseModel


class ExportPackageRecord(BaseModel):
    """Lightweight record returned by the export history endpoint."""
    id: str
    session_id: str
    format: str
    item_count: int
    total_amount: float | None
    total_taxable: float | None
    compliance_score: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkspaceExportGenerateRequest(BaseModel):
    export_password: str
    include_source_documents: bool = False


class WorkspaceExportRecord(BaseModel):
    id: str
    workspace_id: str | None
    filename: str | None
    status: str
    format: str
    encrypted: bool
    kdf: str | None
    encryption_version: str | None
    kdf_params_summary: str | None
    created_at: datetime
    downloaded_at: datetime | None
    file_size: int | None
    sha256: str | None
    item_count: int
    document_count: int | None
    blocking_reasons: str | None

    model_config = {"from_attributes": True}
