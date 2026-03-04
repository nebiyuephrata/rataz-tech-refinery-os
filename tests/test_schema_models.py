from __future__ import annotations

import pytest

from rataz_tech.core.models import (
    BBox,
    ChunkType,
    DocumentProfile,
    DomainHint,
    ExtractionCostTier,
    LayoutComplexity,
    LogicalDocumentUnit,
    OriginType,
    PageIndexNode,
    PageRef,
    ProvenanceChain,
)


def test_bbox_and_page_validators() -> None:
    with pytest.raises(ValueError):
        BBox(x0=1, y0=1, x1=0.5, y1=2)
    with pytest.raises(ValueError):
        PageRef(page_start=2, page_end=1)


def test_recursive_page_index_and_ldu_fields() -> None:
    root = PageIndexNode(
        node_id="root",
        title="Root",
        page_start=1,
        page_end=2,
        children=[PageIndexNode(node_id="child", title="Child", page_start=2, page_end=2)],
    )
    ldu = LogicalDocumentUnit(
        ldu_id="ldu-1",
        content="example",
        chunk_type=ChunkType.TEXT,
        token_count=1,
        page_refs=[PageRef(page_start=1, page_end=1)],
        content_hash="12345678",
        parent_section="root",
        chunk_relationships=["ldu-2"],
    )
    chain = ProvenanceChain(document_name="doc.pdf", page_number=1, content_hash="12345678")

    assert root.children[0].node_id == "child"
    assert ldu.parent_section == "root"
    assert chain.page_number == 1


def test_document_profile_enum_precision() -> None:
    profile = DocumentProfile(
        origin_type=OriginType.NATIVE_DIGITAL,
        layout_complexity=LayoutComplexity.SINGLE_COLUMN,
        language="en",
        domain_hint=DomainHint.FINANCE,
        extraction_cost=ExtractionCostTier.A_FAST_TEXT,
        confidence=0.8,
        char_count=100,
        char_density=100.0,
        image_ratio=0.1,
        font_metadata_present=True,
        table_marker_count=0,
    )
    assert profile.domain_hint == DomainHint.FINANCE
