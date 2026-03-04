from __future__ import annotations

from rataz_tech.indexing.strategies import IndexingStrategy, InvertedIndexStore, InvertedIndexingStrategy


def build_indexer(name: str, store: InvertedIndexStore) -> IndexingStrategy:
    if name == "inverted_index":
        return InvertedIndexingStrategy(store)
    raise ValueError(f"Unknown indexer strategy: {name}")
