from __future__ import annotations

from rataz_tech.core.models import BBox, ChunkType, DocumentProfile, DomainHint, ExtractionCostTier, ExtractedDocument, ExtractedFigure, ExtractedTable, LayoutComplexity, LogicalDocumentUnit, OriginType, PageIndexNode, PageRef
from rataz_tech.chunking.semantic_engine import ChunkValidator, build_ldus


def _profile() -> DocumentProfile:
    return DocumentProfile(
        origin_type=OriginType.NATIVE_DIGITAL,
        layout_complexity=LayoutComplexity.SINGLE_COLUMN,
        language="en",
        domain_hint=DomainHint.FINANCE,
        extraction_cost=ExtractionCostTier.B_LAYOUT_AWARE,
        confidence=0.9,
        char_count=1200,
        char_density=1200.0,
        image_ratio=0.1,
        font_metadata_present=True,
        table_marker_count=12,
    )


def test_semantic_chunking_builds_valid_ldus_with_rules() -> None:
    doc = ExtractedDocument(
        document_id="d1",
        profile=_profile(),
        text_blocks=[
            LogicalDocumentUnit(
                ldu_id="raw-1",
                content="1. first item\\n2. second item\\nSee Section Revenue",
                chunk_type=ChunkType.TEXT,
                token_count=11,
                page_refs=[PageRef(page_start=1, page_end=1)],
                bounding_box=BBox(x0=0, y0=0, x1=1, y1=0.5),
                content_hash="aaaaaaaa",
                parent_section="Revenue",
                chunk_relationships=[],
            )
        ],
        tables=[
            ExtractedTable(
                table_id="t1",
                headers=["metric", "value"],
                rows=[["revenue", "4200"]],
                page_number=1,
                bounding_box=BBox(x0=0, y0=0.5, x1=1, y1=0.8),
            )
        ],
        figures=[
            ExtractedFigure(
                figure_id="f1",
                caption="Revenue trend",
                page_number=1,
                bounding_box=BBox(x0=0, y0=0.8, x1=1, y1=1),
            )
        ],
        page_index=PageIndexNode(node_id="root", title="Doc", page_start=1, page_end=1, children=[]),
        provenance_chains=[],
    )

    ldus = build_ldus(doc, max_tokens=128)
    validator = ChunkValidator(max_tokens=128)
    validated = validator.validate(ldus)

    assert validated
    table_ldu = [ldu for ldu in validated if ldu.chunk_type == ChunkType.TABLE][0]
    assert "metric" in table_ldu.content and "revenue" in table_ldu.content
    figure_ldu = [ldu for ldu in validated if ldu.chunk_type == ChunkType.FIGURE][0]
    assert figure_ldu.metadata.get("caption") == "Revenue trend"
    text_ldu = [ldu for ldu in validated if ldu.chunk_type == ChunkType.TEXT][0]
    assert text_ldu.parent_section == "Revenue"
    assert any(rel.startswith("xref:") for rel in text_ldu.chunk_relationships)
