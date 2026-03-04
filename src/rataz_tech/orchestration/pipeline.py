from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from rataz_tech.chunking.factory import build_chunker
from rataz_tech.core.config import Settings
from rataz_tech.core.models import (
    AuditEvent,
    DocumentInput,
    PipelineResult,
    QueryRequest,
    QueryResponse,
)
from rataz_tech.extraction.factory import build_extractor
from rataz_tech.indexing.factory import build_indexer
from rataz_tech.indexing.strategies import InvertedIndexStore
from rataz_tech.localization.service import LocalizationService
from rataz_tech.normalization.factory import build_normalizer
from rataz_tech.querying.factory import build_query_engine


class RefineryPipeline:
    def __init__(self, settings: Settings, locale_dir: Path) -> None:
        self.settings = settings
        self.store = InvertedIndexStore()

        self.extractor = build_extractor(settings.components.extractor, settings)
        self.normalizer = build_normalizer(settings.components.normalizer)
        self.chunker = build_chunker(settings.components.chunker, settings.pipeline)
        self.indexer = build_indexer(settings.components.indexer, self.store)
        self.query_engine = build_query_engine(settings.components.query_engine, self.store, settings.pipeline)

        self.i18n = LocalizationService(
            default_lang=settings.app.default_language,
            supported_languages=settings.app.supported_languages,
        )
        self.i18n.load(locale_dir)

    def ingest(self, doc: DocumentInput) -> PipelineResult:
        trace_id = f"ingest-{uuid4()}"
        extracted = self.extractor.extract(doc)
        self._stamp_audit(extracted.audit, trace_id)
        extracted.trace_id = trace_id

        normalized = self.normalizer.normalize(extracted)
        self._stamp_audit(normalized.audit, trace_id)
        normalized.trace_id = trace_id

        chunked = self.chunker.chunk(normalized)
        self._stamp_audit(chunked.audit, trace_id)
        chunked.trace_id = trace_id

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

    def query(self, request: QueryRequest) -> QueryResponse:
        trace_id = f"query-{uuid4()}"
        response = self.query_engine.query(request)
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
