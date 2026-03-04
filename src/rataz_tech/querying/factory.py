from __future__ import annotations

from rataz_tech.core.config import PipelineConfig
from rataz_tech.indexing.strategies import InvertedIndexStore
from rataz_tech.querying.strategies import HybridDeterministicQueryStrategy, QueryStrategy


def build_query_engine(name: str, store: InvertedIndexStore, pipeline: PipelineConfig) -> QueryStrategy:
    if name == "hybrid":
        return HybridDeterministicQueryStrategy(store=store, config=pipeline)
    raise ValueError(f"Unknown query strategy: {name}")
