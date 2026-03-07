from __future__ import annotations

from rataz_tech.core.models import AuditEvent, Chunk, ChunkingResult, ProvenanceRecord, SpatialProvenance, StageName
from rataz_tech.indexing.strategies import InvertedIndexStore, InvertedIndexingStrategy


def _chunking_result() -> ChunkingResult:
    prov = ProvenanceRecord(
        source_uri="local://d",
        extractor="t",
        record_id="r1",
        confidence=1.0,
        spatial=SpatialProvenance(page=1, x0=0, y0=0, x1=1, y1=1),
    )
    return ChunkingResult(
        document_id="d",
        chunks=[Chunk(chunk_id="c1", document_id="d", text="alpha beta", source_unit_ids=["u1"], provenance=[prov])],
        audit=[AuditEvent(stage=StageName.CHUNKING, message="seed")],
    )


def test_inverted_index_deduplicates_postings_on_reindex() -> None:
    store = InvertedIndexStore()
    strategy = InvertedIndexingStrategy(store)
    result = _chunking_result()

    strategy.index(result)
    strategy.index(result)

    assert len(store.postings["alpha"]) == 1
    assert len(store.postings["beta"]) == 1
