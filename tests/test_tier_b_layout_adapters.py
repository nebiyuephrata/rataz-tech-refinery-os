from __future__ import annotations

from rataz_tech.core.models import (
    BBox,
    DocumentInput,
    DocumentProfile,
    DomainHint,
    ExtractionCostTier,
    LayoutComplexity,
    OriginType,
)
from rataz_tech.extraction.layout_adapters import LayoutAdapterResult, ParsedFigure, ParsedLayoutBlock, ParsedTable
from rataz_tech.extraction.strategies import LayoutAwareExtractionStrategy


class FakeLayoutAdapter:
    provider_name = "fake_layout"

    def available(self) -> bool:
        return True

    def parse(self, document: DocumentInput) -> LayoutAdapterResult:
        return LayoutAdapterResult(
            blocks=[
                ParsedLayoutBlock(page=1, text="Revenue section", bbox=BBox(x0=0, y0=0, x1=50, y1=10), reading_order=1),
                ParsedLayoutBlock(page=1, text="Profit section", bbox=BBox(x0=0, y0=11, x1=50, y1=20), reading_order=2),
            ],
            tables=[
                ParsedTable(
                    page=1,
                    headers=["col1", "col2"],
                    rows=[["1", "2"]],
                    bbox=BBox(x0=0, y0=21, x1=50, y1=30),
                )
            ],
            figures=[ParsedFigure(page=1, caption="Figure A", bbox=BBox(x0=0, y0=31, x1=50, y1=40))],
        )


def _profile() -> DocumentProfile:
    return DocumentProfile(
        origin_type=OriginType.NATIVE_DIGITAL,
        layout_complexity=LayoutComplexity.MULTI_COLUMN,
        language="en",
        domain_hint=DomainHint.FINANCE,
        extraction_cost=ExtractionCostTier.B_LAYOUT_AWARE,
        confidence=0.9,
        char_count=1000,
        char_density=1000.0,
        image_ratio=0.1,
        font_metadata_present=True,
        table_marker_count=2,
    )


def test_layout_strategy_maps_adapter_output_to_internal_schema() -> None:
    strategy = LayoutAwareExtractionStrategy(tool_name="docling_layout", adapter=FakeLayoutAdapter())
    result = strategy.extract(
        DocumentInput(document_id="doc-1", source_uri="local://doc-1.pdf", content="seed", mime_type="application/pdf"),
        _profile(),
    )

    assert result.extracted_document is not None
    doc = result.extracted_document
    assert len(doc.text_blocks) == 2
    assert doc.text_blocks[0].content == "Revenue section"
    assert len(doc.tables) == 1
    assert len(doc.figures) == 1
    assert result.strategy_used == "docling_layout"
    assert any(a.metadata.get("provider") == "fake_layout" for a in result.audit)


def test_layout_strategy_falls_back_when_adapter_unavailable() -> None:
    class UnavailableAdapter(FakeLayoutAdapter):
        provider_name = "fake_unavailable"

        def available(self) -> bool:
            return False

    strategy = LayoutAwareExtractionStrategy(tool_name="mineru_layout", adapter=UnavailableAdapter())
    result = strategy.extract(
        DocumentInput(document_id="doc-2", source_uri="local://doc-2.pdf", content="fallback content", mime_type="application/pdf"),
        _profile(),
    )

    assert result.extracted_document is not None
    assert len(result.extracted_document.text_blocks) == 1
    assert result.extracted_document.text_blocks[0].content == "fallback content"
    assert any(a.metadata.get("available") == "false" for a in result.audit)
