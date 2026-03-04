from __future__ import annotations

from pathlib import Path

from rataz_tech.chunking.factory import build_chunker
from rataz_tech.core.config import Settings
from rataz_tech.core.models import DocumentInput, PipelineResult, QueryRequest, QueryResponse
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

        self.extractor = build_extractor(settings.components.extractor)
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
        extracted = self.extractor.extract(doc)
        normalized = self.normalizer.normalize(extracted)
        chunked = self.chunker.chunk(normalized)
        indexed = self.indexer.index(chunked)
        return PipelineResult(
            extraction=extracted,
            normalization=normalized,
            chunking=chunked,
            indexing=indexed,
        )

    def query(self, request: QueryRequest) -> QueryResponse:
        response = self.query_engine.query(request)
        if not response.hits and request.language in self.settings.app.supported_languages:
            response.reason = self.i18n.t("query.no_hits", request.language)
        elif response.reason and "Low confidence" in response.reason:
            response.reason = self.i18n.t("query.low_confidence", request.language)
        return response
