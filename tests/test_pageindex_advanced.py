from __future__ import annotations

from pathlib import Path

from rataz_tech.core.models import AuditEvent, Chunk, ChunkingResult, ProvenanceRecord, SpatialProvenance, StageName
from rataz_tech.pageindex.service import PageIndexBuilder, PageIndexRetriever


def _chunk(i: int, text: str, page: int) -> Chunk:
    return Chunk(
        chunk_id=f"c{i}",
        document_id="d1",
        text=text,
        source_unit_ids=[f"u{i}"],
        provenance=[ProvenanceRecord(source_uri="local://d1", extractor="t", record_id=f"r{i}", confidence=1.0, spatial=SpatialProvenance(page=page, x0=0, y0=0, x1=1, y1=1))],
    )


def test_pageindex_populates_advanced_attributes_and_serializes(tmp_path: Path) -> None:
    builder = PageIndexBuilder(group_size=2, output_path=str(tmp_path / "indexes"))
    chunked = ChunkingResult(
        document_id="d1",
        chunks=[
            _chunk(1, "Revenue section contains 4200 and EBITDA 900", 1),
            _chunk(2, "Tax section contains 300", 2),
        ],
        audit=[AuditEvent(stage=StageName.CHUNKING, message="ok")],
    )
    result = builder.build(chunked, trace_id="t1")

    node = result.root.children[0]
    assert node.child_sections == []
    assert node.key_entities
    assert node.data_types_present

    out = builder.serialize(result)
    assert Path(out).exists()

    retriever = PageIndexRetriever()
    resp = retriever.query(result.root, document_id="d1", query="revenue", top_k=2)
    assert resp.hits
