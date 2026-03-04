from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field

from rataz_tech.core.models import PipelineResult


class HealthResponse(BaseModel):
    status: str
    app: str
    storage_backend: str


class ApiErrorResponse(BaseModel):
    error: str
    trace_id: Optional[str] = None


class RequestAuditRecord(BaseModel):
    route: str
    method: str
    trace_id: str
    document_id: Optional[str] = None
    timestamp_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RequestAuditListResponse(BaseModel):
    records: List[RequestAuditRecord]


class StoredExtractionResponse(BaseModel):
    document_id: str
    trace_id: str
    extracted_at_utc: datetime
    pipeline_result: PipelineResult
