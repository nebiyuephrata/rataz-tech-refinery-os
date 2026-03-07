from __future__ import annotations

from rataz_tech.core.config import PipelineConfig
from rataz_tech.indexing.strategies import InvertedIndexStore
from rataz_tech.querying.strategies import (
    HybridDeterministicQueryStrategy,
    QueryStrategy,
    SemanticHybridQueryStrategy,
)


def build_query_engine(name: str, store: InvertedIndexStore, pipeline: PipelineConfig) -> QueryStrategy:
    if name == "hybrid":
        if pipeline.enable_semantic_navigation and pipeline.semantic_query.enabled:
            return SemanticHybridQueryStrategy(store=store, config=pipeline)
        return HybridDeterministicQueryStrategy(store=store, config=pipeline)
    raise ValueError(f"Unknown query strategy: {name}")
