from __future__ import annotations

from rataz_tech.core.models import (
    AuditEvent,
    BBox,
    Chunk,
    ChunkType,
    ChunkingResult,
    PageRef,
    ProvenanceRecord,
    SpatialProvenance,
    StageName,
)
from rataz_tech.indexing.strategies import InvertedIndexStore, InvertedIndexingStrategy


def test_vector_ingestion_keeps_complete_chunk_metadata() -> None:
    store = InvertedIndexStore()
    strategy = InvertedIndexingStrategy(store)

    chunk = Chunk(
        chunk_id="c1",
        document_id="d1",
        text="Revenue is 4200",
        source_unit_ids=["u1"],
        provenance=[
            ProvenanceRecord(
                source_uri="local://d1",
                extractor="test",
                record_id="r1",
                confidence=1.0,
                spatial=SpatialProvenance(page=2, x0=0.1, y0=0.2, x1=0.8, y1=0.9),
            )
        ],
        chunk_type=ChunkType.TABLE,
        page_refs=[PageRef(page_start=2, page_end=2)],
        bounding_box=BBox(x0=0.1, y0=0.2, x1=0.8, y1=0.9),
        parent_section="Revenue",
        content_hash="1234567890abcdef",
    )

    strategy.index(
        ChunkingResult(
            document_id="d1",
            chunks=[chunk],
            audit=[AuditEvent(stage=StageName.CHUNKING, message="seed")],
        )
    )

    meta = store.metadata["c1"]
    assert meta["chunk_type"] == "table"
    assert meta["page_refs"] == [{"page_start": 2, "page_end": 2}]
    assert meta["content_hash"] == "1234567890abcdef"
    assert meta["parent_section"] == "Revenue"
