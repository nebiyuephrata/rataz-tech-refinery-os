from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from rataz_tech.chunking.factory import build_chunker
from rataz_tech.core.config import Settings
from rataz_tech.core.models import (
    AuditEvent,
    DocumentInput,
    PageIndexBuildResult,
    PageIndexQueryRequest,
    PageIndexQueryResponse,
    PipelineResult,
    QueryRequest,
    QueryResponse,
)
from rataz_tech.extraction.factory import build_extractor
from rataz_tech.indexing.factory import build_indexer
from rataz_tech.indexing.strategies import InvertedIndexStore
from rataz_tech.localization.service import LocalizationService
from rataz_tech.normalization.factory import build_normalizer
from rataz_tech.orchestration.five_stage import (
    PageIndexBuilderStage,
    QueryInterfaceStage,
    SemanticChunkingStage,
    StructureExtractionStage,
    TriageStage,
    inject_stage_audit,
)
from rataz_tech.pageindex.service import PageIndexBuilder, PageIndexRetriever
from rataz_tech.querying.factory import build_query_engine


class RefineryPipeline:
    def __init__(self, settings: Settings, locale_dir: Path) -> None:
        self.settings = settings
        self.store = InvertedIndexStore()

        extractor = build_extractor(settings.components.extractor, settings)
        normalizer = build_normalizer(settings.components.normalizer)
        chunker = build_chunker(settings.components.chunker, settings.pipeline)
        indexer = build_indexer(settings.components.indexer, self.store)
        query_engine = build_query_engine(settings.components.query_engine, self.store, settings.pipeline)

        self.triage_stage = TriageStage(settings)
        self.structure_stage = StructureExtractionStage(extractor)
        self.semantic_stage = SemanticChunkingStage(normalizer, chunker)
        self.pageindex_stage = PageIndexBuilderStage(PageIndexBuilder())
        self.query_stage = QueryInterfaceStage(query_engine, PageIndexRetriever())
        self.indexer = indexer

        self._pageindex_by_doc: dict[str, PageIndexBuildResult] = {}

        self.i18n = LocalizationService(
            default_lang=settings.app.default_language,
            supported_languages=settings.app.supported_languages,
        )
        self.i18n.load(locale_dir)

    def ingest(self, doc: DocumentInput) -> PipelineResult:
        trace_id = f"ingest-{uuid4()}"

        triage = self.triage_stage.run(doc)
        extracted = self.structure_stage.run(doc)
        extracted.profile = triage.profile
        self._stamp_audit(extracted.audit, trace_id)
        inject_stage_audit(
            extracted.audit,
            stage=extracted.audit[0].stage,
            message="Stage 1 triage executed",
            metadata={
                "origin_type": triage.profile.origin_type.value,
                "layout_complexity": triage.profile.layout_complexity.value,
                "domain_hint": triage.profile.domain_hint.value,
            },
        )
        extracted.trace_id = trace_id

        normalized, chunked = self.semantic_stage.run(extracted)
        self._stamp_audit(normalized.audit, trace_id)
        normalized.trace_id = trace_id

        self._stamp_audit(chunked.audit, trace_id)
        chunked.trace_id = trace_id

        pageindex = self.pageindex_stage.run(chunked, trace_id=trace_id)
        self._pageindex_by_doc[doc.document_id] = pageindex
        if extracted.extracted_document is not None:
            extracted.extracted_document.page_index = pageindex.root
        inject_stage_audit(
            chunked.audit,
            stage=chunked.audit[0].stage,
            message="Stage 4 page index built",
            metadata={"node_count": str(pageindex.node_count)},
        )

        indexed = self.indexer.index(chunked)
        self._stamp_audit(indexed.audit, trace_id)
        indexed.trace_id = trace_id

        return PipelineResult(
            trace_id=trace_id,
            extraction=extracted,
            normalization=normalized,
            chunking=chunked,
            indexing=indexed,
        )

    def get_pageindex(self, document_id: str) -> PageIndexBuildResult | None:
        return self._pageindex_by_doc.get(document_id)

    def query_pageindex(self, request: PageIndexQueryRequest) -> PageIndexQueryResponse:
        trace_id = f"pageindex-query-{uuid4()}"
        built = self._pageindex_by_doc.get(request.document_id)
        if built is None:
            return PageIndexQueryResponse(document_id=request.document_id, query=request.query, trace_id=trace_id, hits=[], audit=[])
        response = self.query_stage.run_pageindex_query(built.root, request, trace_id=trace_id)
        self._stamp_audit(response.audit, trace_id)
        return response

    def query(self, request: QueryRequest) -> QueryResponse:
        trace_id = f"query-{uuid4()}"
        response = self.query_stage.run_query(request)
        self._stamp_audit(response.audit, trace_id)
        response.trace_id = trace_id
        if not response.hits and request.language in self.settings.app.supported_languages:
            response.reason = self.i18n.t("query.no_hits", request.language)
        elif response.reason and "Low confidence" in response.reason:
            response.reason = self.i18n.t("query.low_confidence", request.language)
        return response

    @staticmethod
    def _stamp_audit(events: list[AuditEvent], trace_id: str) -> None:
        for event in events:
            event.trace_id = trace_id
