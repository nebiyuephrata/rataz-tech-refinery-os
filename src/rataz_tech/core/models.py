from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class StageName(str, Enum):
    EXTRACTION = "extraction"
    NORMALIZATION = "normalization"
    CHUNKING = "chunking"
    INDEXING = "indexing"
    QUERYING = "querying"


class OriginType(str, Enum):
    NATIVE_DIGITAL = "native_digital"
    SCANNED_IMAGE = "scanned_image"
    MIXED = "mixed"


class LayoutComplexity(str, Enum):
    SINGLE_COLUMN = "single_column"
    MULTI_COLUMN = "multi_column"
    TABLE_HEAVY = "table_heavy"
    FIGURE_HEAVY = "figure_heavy"
    MIXED = "mixed"


class DomainHint(str, Enum):
    FINANCE = "finance"
    LEGAL = "legal"
    ASSESSMENT = "assessment"
    FISCAL = "fiscal"
    GENERAL = "general"


class ExtractionCostTier(str, Enum):
    A_FAST_TEXT = "A_fast_text"
    B_LAYOUT_AWARE = "B_layout_aware"
    C_VISION_AUGMENTED = "C_vision_augmented"


class ChunkType(str, Enum):
    TEXT = "text"
    TABLE = "table"
    FIGURE = "figure"


class BBox(BaseModel):
    x0: float = Field(ge=0)
    y0: float = Field(ge=0)
    x1: float = Field(ge=0)
    y1: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_axis_order(self) -> BBox:
        if self.x1 < self.x0 or self.y1 < self.y0:
            raise ValueError("bbox must satisfy x1>=x0 and y1>=y0")
        return self


class PageRef(BaseModel):
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_range(self) -> PageRef:
        if self.page_end < self.page_start:
            raise ValueError("page_end must be >= page_start")
        return self


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


class ProvenanceChain(BaseModel):
    document_name: str
    page_number: int = Field(ge=1)
    bbox: Optional[BBox] = None
    content_hash: str = Field(min_length=8)


class DocumentProfile(BaseModel):
    origin_type: OriginType
    layout_complexity: LayoutComplexity
    language: str = "en"
    domain_hint: DomainHint
    extraction_cost: ExtractionCostTier
    confidence: float = Field(ge=0.0, le=1.0)

    char_count: int = Field(ge=0)
    char_density: float = Field(ge=0.0)
    image_ratio: float = Field(ge=0.0, le=1.0)
    font_metadata_present: bool
    table_marker_count: int = Field(ge=0)

    zero_text: bool = False
    mixed_mode_pages: bool = False
    form_fillable: bool = False


class LogicalDocumentUnit(BaseModel):
    ldu_id: str
    content: str
    chunk_type: ChunkType
    token_count: int = Field(ge=0)
    page_refs: List[PageRef]
    bounding_box: Optional[BBox] = None
    content_hash: str = Field(min_length=8)
    parent_section: Optional[str] = None
    chunk_relationships: List[str] = Field(default_factory=list)
    metadata: Dict[str, str] = Field(default_factory=dict)


class PageIndexNode(BaseModel):
    node_id: str
    title: str
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    summary: str = ""
    keywords: List[str] = Field(default_factory=list)
    key_entities: List[str] = Field(default_factory=list)
    data_types_present: List[str] = Field(default_factory=list)
    chunk_ids: List[str] = Field(default_factory=list)
    child_sections: List[str] = Field(default_factory=list)
    children: List["PageIndexNode"] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_range(self) -> PageIndexNode:
        if self.page_end < self.page_start:
            raise ValueError("page_end must be >= page_start")
        return self


class ExtractedTable(BaseModel):
    table_id: str
    headers: List[str]
    rows: List[List[str]]
    page_number: int = Field(ge=1)
    bounding_box: Optional[BBox] = None


class ExtractedFigure(BaseModel):
    figure_id: str
    caption: str
    page_number: int = Field(ge=1)
    bounding_box: Optional[BBox] = None


class ExtractedDocument(BaseModel):
    document_id: str
    profile: DocumentProfile
    text_blocks: List[LogicalDocumentUnit] = Field(default_factory=list)
    tables: List[ExtractedTable] = Field(default_factory=list)
    figures: List[ExtractedFigure] = Field(default_factory=list)
    page_index: PageIndexNode
    provenance_chains: List[ProvenanceChain] = Field(default_factory=list)


class AuditEvent(BaseModel):
    stage: StageName
    message: str
    trace_id: str = ""
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
    trace_id: str = ""
    profile: Optional[DocumentProfile] = None
    extracted_document: Optional[ExtractedDocument] = None
    strategy_used: str = ""
    strategy_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    escalation_path: List[str] = Field(default_factory=list)
    review_required: bool = False
    units: List[ExtractedUnit]
    audit: List[AuditEvent]


class NormalizedUnit(BaseModel):
    unit_id: str
    normalized_text: str
    provenance: ProvenanceRecord


class NormalizationResult(BaseModel):
    document_id: str
    trace_id: str = ""
    units: List[NormalizedUnit]
    audit: List[AuditEvent]


class Chunk(BaseModel):
    chunk_id: str
    document_id: str
    text: str
    source_unit_ids: List[str]
    provenance: List[ProvenanceRecord]
    chunk_type: ChunkType = ChunkType.TEXT
    page_refs: List[PageRef] = Field(default_factory=lambda: [PageRef(page_start=1, page_end=1)])
    bounding_box: Optional[BBox] = None
    parent_section: Optional[str] = None
    content_hash: str = ""
    chunk_relationships: List[str] = Field(default_factory=list)
    metadata: Dict[str, str] = Field(default_factory=dict)


class ChunkingResult(BaseModel):
    document_id: str
    trace_id: str = ""
    chunks: List[Chunk]
    audit: List[AuditEvent]


class IndexedChunk(BaseModel):
    chunk_id: str
    text: str
    token_count: int


class IndexResult(BaseModel):
    document_id: str
    trace_id: str = ""
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
    trace_id: str = ""
    hits: List[QueryHit]
    escalated: bool = False
    reason: Optional[str] = None
    audit: List[AuditEvent]


class NumericalFact(BaseModel):
    document_id: str
    metric: str
    value: float
    unit: str = ""
    page_number: int = Field(ge=1, default=1)
    content_hash: str = Field(min_length=8)
    source_text: str


class StructuredQueryRequest(BaseModel):
    document_id: str
    query: str
    limit: int = Field(default=5, ge=1, le=100)


class StructuredQueryResponse(BaseModel):
    document_id: str
    query: str
    rows: List[NumericalFact] = Field(default_factory=list)
    audit: List[AuditEvent] = Field(default_factory=list)


class ClaimVerificationRequest(BaseModel):
    document_id: str
    claim: str


class ClaimVerificationResponse(BaseModel):
    document_id: str
    claim: str
    verified: bool
    status: str
    citation: Optional[ProvenanceChain] = None
    audit: List[AuditEvent] = Field(default_factory=list)


class PageIndexBuildResult(BaseModel):
    document_id: str
    trace_id: str = ""
    root: PageIndexNode
    node_count: int = Field(ge=1)
    built_at_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PageIndexQueryRequest(BaseModel):
    document_id: str
    query: str
    top_k: int = Field(ge=1, le=20, default=5)


class PageIndexHit(BaseModel):
    node_id: str
    title: str
    score: float
    summary: str
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    reasoning_path: List[str] = Field(default_factory=list)
    provenance: List[ProvenanceChain] = Field(default_factory=list)


class PageIndexQueryResponse(BaseModel):
    document_id: str
    query: str
    trace_id: str = ""
    hits: List[PageIndexHit]
    audit: List[AuditEvent]


class PipelineResult(BaseModel):
    trace_id: str = ""
    extraction: ExtractionResult
    normalization: NormalizationResult
    chunking: ChunkingResult
    indexing: IndexResult


PageIndexNode.model_rebuild()
