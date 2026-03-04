from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class StageName(str, Enum):
    EXTRACTION = "extraction"
    NORMALIZATION = "normalization"
    CHUNKING = "chunking"
    INDEXING = "indexing"
    QUERYING = "querying"


class SpatialProvenance(BaseModel):
    page: int = Field(ge=1)
    x0: float = Field(ge=0)
    y0: float = Field(ge=0)
    x1: float = Field(ge=0)
    y1: float = Field(ge=0)


class ProvenanceRecord(BaseModel):
    source_uri: str
    extractor: str
    record_id: str
    spatial: Optional[SpatialProvenance] = None
    confidence: float = Field(ge=0.0, le=1.0)


class AuditEvent(BaseModel):
    stage: StageName
    message: str
    timestamp_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, str] = Field(default_factory=dict)


class DocumentInput(BaseModel):
    document_id: str
    source_uri: str
    content: str
    mime_type: str = "text/plain"


class ExtractedUnit(BaseModel):
    unit_id: str
    text: str
    provenance: ProvenanceRecord


class ExtractionResult(BaseModel):
    document_id: str
    units: List[ExtractedUnit]
    audit: List[AuditEvent]


class NormalizedUnit(BaseModel):
    unit_id: str
    normalized_text: str
    provenance: ProvenanceRecord


class NormalizationResult(BaseModel):
    document_id: str
    units: List[NormalizedUnit]
    audit: List[AuditEvent]


class Chunk(BaseModel):
    chunk_id: str
    document_id: str
    text: str
    source_unit_ids: List[str]
    provenance: List[ProvenanceRecord]


class ChunkingResult(BaseModel):
    document_id: str
    chunks: List[Chunk]
    audit: List[AuditEvent]


class IndexedChunk(BaseModel):
    chunk_id: str
    text: str
    token_count: int


class IndexResult(BaseModel):
    document_id: str
    indexed: List[IndexedChunk]
    audit: List[AuditEvent]


class QueryRequest(BaseModel):
    query: str
    language: str = "en"
    max_results: int = Field(ge=1, le=50)


class QueryHit(BaseModel):
    chunk_id: str
    score: float
    snippet: str
    provenance: List[ProvenanceRecord]


class QueryResponse(BaseModel):
    query: str
    language: str
    hits: List[QueryHit]
    escalated: bool = False
    reason: Optional[str] = None
    audit: List[AuditEvent]


class PipelineResult(BaseModel):
    extraction: ExtractionResult
    normalization: NormalizationResult
    chunking: ChunkingResult
    indexing: IndexResult
