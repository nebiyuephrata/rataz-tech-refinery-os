from __future__ import annotations

from dataclasses import dataclass

from rataz_tech.chunking.strategies import ChunkingStrategy
from rataz_tech.core.config import Settings
from rataz_tech.core.models import (
    AuditEvent,
    ChunkingResult,
    DocumentInput,
    ExtractionResult,
    IndexResult,
    NormalizationResult,
    PageIndexBuildResult,
    PageIndexQueryRequest,
    PageIndexQueryResponse,
    QueryRequest,
    QueryResponse,
    StageName,
)
from rataz_tech.extraction.factory import AutoTriageExtractionStrategy
from rataz_tech.extraction.triage import TriageDecision, build_triage_decision
from rataz_tech.normalization.strategies import NormalizationStrategy
from rataz_tech.pageindex.service import PageIndexBuilder, PageIndexRetriever
from rataz_tech.querying.strategies import QueryStrategy


@dataclass
class StageOutputs:
    triage: TriageDecision
    extraction: ExtractionResult
    normalization: NormalizationResult
    chunking: ChunkingResult
    pageindex: PageIndexBuildResult
    indexing: IndexResult


class TriageStage:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def run(self, document: DocumentInput) -> TriageDecision:
        return build_triage_decision(document, self.settings.extraction)


class StructureExtractionStage:
    def __init__(self, extractor: AutoTriageExtractionStrategy) -> None:
        self.extractor = extractor

    def run(self, document: DocumentInput) -> ExtractionResult:
        return self.extractor.extract(document)


class SemanticChunkingStage:
    def __init__(self, normalizer: NormalizationStrategy, chunker: ChunkingStrategy) -> None:
        self.normalizer = normalizer
        self.chunker = chunker

    def run(self, extracted: ExtractionResult) -> tuple[NormalizationResult, ChunkingResult]:
        normalized = self.normalizer.normalize(extracted)
        chunked = self.chunker.chunk(normalized)
        return normalized, chunked


class PageIndexBuilderStage:
    def __init__(self, builder: PageIndexBuilder) -> None:
        self.builder = builder

    def run(self, chunked: ChunkingResult, trace_id: str = "") -> PageIndexBuildResult:
        return self.builder.build(chunked, trace_id=trace_id)


class QueryInterfaceStage:
    def __init__(self, query_engine: QueryStrategy, retriever: PageIndexRetriever) -> None:
        self.query_engine = query_engine
        self.retriever = retriever

    def run_query(self, request: QueryRequest) -> QueryResponse:
        return self.query_engine.query(request)

    def run_pageindex_query(
        self,
        root,
        request: PageIndexQueryRequest,
        trace_id: str = "",
    ) -> PageIndexQueryResponse:
        return self.retriever.query(root=root, document_id=request.document_id, query=request.query, top_k=request.top_k, trace_id=trace_id)


def inject_stage_audit(events: list[AuditEvent], stage: StageName, message: str, metadata: dict[str, str] | None = None) -> None:
    events.append(AuditEvent(stage=stage, message=message, metadata=metadata or {}))
