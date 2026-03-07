from __future__ import annotations

from rataz_tech.core.config import load_settings
from rataz_tech.core.models import ProvenanceRecord, QueryRequest
from rataz_tech.indexing.strategies import InvertedIndexStore
from rataz_tech.querying.factory import build_query_engine
from rataz_tech.querying.strategies import HybridDeterministicQueryStrategy, SemanticHybridQueryStrategy


def _seed_store() -> InvertedIndexStore:
    store = InvertedIndexStore()
    store.chunks["c1"] = "revenue growth statement"
    store.chunks["c2"] = "random noise content"
    store.provenance["c1"] = [
        ProvenanceRecord(source_uri="local://d", extractor="test", record_id="p1", confidence=1.0)
    ]
    store.provenance["c2"] = [
        ProvenanceRecord(source_uri="local://d", extractor="test", record_id="p2", confidence=1.0)
    ]
    store.postings["revenue"].add("c1")
    return store


def test_factory_uses_semantic_strategy_when_enabled() -> None:
    settings = load_settings("configs/settings.yaml")
    settings.pipeline.enable_semantic_navigation = True
    settings.pipeline.semantic_query.enabled = True
    settings.pipeline.semantic_query.embedder_provider = "hashing"
    settings.pipeline.semantic_query.vector_store_provider = "inmemory"

    engine = build_query_engine(settings.components.query_engine, _seed_store(), settings.pipeline)
    assert isinstance(engine, SemanticHybridQueryStrategy)


def test_factory_uses_deterministic_strategy_when_semantic_disabled() -> None:
    settings = load_settings("configs/settings.yaml")
    settings.pipeline.enable_semantic_navigation = False
    settings.pipeline.semantic_query.enabled = False

    engine = build_query_engine(settings.components.query_engine, _seed_store(), settings.pipeline)
    assert isinstance(engine, HybridDeterministicQueryStrategy)


def test_semantic_strategy_falls_back_from_optional_backends() -> None:
    settings = load_settings("configs/settings.yaml")
    settings.pipeline.enable_semantic_navigation = True
    settings.pipeline.semantic_query.enabled = True
    settings.pipeline.semantic_query.embedder_provider = "bge-small"
    settings.pipeline.semantic_query.vector_store_provider = "faiss"

    engine = build_query_engine(settings.components.query_engine, _seed_store(), settings.pipeline)
    response = engine.query(QueryRequest(query="revenue", language="en", max_results=3))

    assert response.hits
    assert response.hits[0].chunk_id == "c1"
    assert response.audit
    metadata = response.audit[0].metadata
    assert metadata.get("semantic_enabled") == "true"
    assert metadata.get("embedder_provider") in {"hashing", "bge-small"}
    assert metadata.get("vector_store_provider") in {"inmemory", "faiss"}
