from __future__ import annotations

from rataz_tech.core.models import Chunk, ProvenanceRecord
from rataz_tech.querying.semantic import HybridRetriever, SemanticQueryConfig


def _chunk(cid: str, text: str) -> Chunk:
    return Chunk(
        chunk_id=cid,
        document_id="d",
        text=text,
        source_unit_ids=[f"u-{cid}"],
        provenance=[ProvenanceRecord(source_uri="local://d", extractor="t", record_id=f"r-{cid}", confidence=1.0)],
    )


def test_hybrid_retriever_ranks_semantic_match() -> None:
    retriever = HybridRetriever(SemanticQueryConfig(enabled=True, top_k=5, lexical_weight=0.5, semantic_weight=0.5))
    retriever.add_chunks([_chunk("c1", "financial revenue statement"), _chunk("c2", "random unrelated token")])

    hits = retriever.query("income and revenue", top_k=2)
    assert hits
    assert hits[0].chunk_id == "c1"


def test_hybrid_retriever_falls_back_to_lexical_when_disabled() -> None:
    retriever = HybridRetriever(SemanticQueryConfig(enabled=False, top_k=5, lexical_weight=1.0, semantic_weight=0.0))
    retriever.add_chunks([_chunk("c1", "alpha beta"), _chunk("c2", "gamma delta")])

    hits = retriever.query("alpha", top_k=2)
    assert hits
    assert hits[0].chunk_id == "c1"

class CountingEmbedder:
    provider_name = "counting"

    def __init__(self) -> None:
        self.calls = 0

    def embed(self, text: str) -> list[float]:
        self.calls += 1
        return [1.0, 0.0]


def test_hybrid_retriever_skips_reembedding_unchanged_chunks() -> None:
    embedder = CountingEmbedder()
    retriever = HybridRetriever(SemanticQueryConfig(enabled=True, top_k=5), embedder=embedder)
    chunk = _chunk("c1", "same text")

    retriever.add_chunks([chunk])
    retriever.add_chunks([chunk])

    assert embedder.calls == 1
