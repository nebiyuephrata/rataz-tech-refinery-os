from __future__ import annotations

from rataz_tech.core.config import load_settings
from rataz_tech.core.models import BBox, DocumentInput, DocumentProfile, DomainHint, ExtractionCostTier, LayoutComplexity, OriginType
from rataz_tech.extraction.factory import build_extractor
from rataz_tech.extraction.layout_adapters import LayoutAdapter, LayoutAdapterResult, ParsedLayoutBlock, build_layout_adapter, register_layout_adapter
from rataz_tech.extraction.ocr_adapters import (
    OCRAdapter,
    OCRAdapterResult,
    OCRTextBlock,
    TableAdapter,
    TableAdapterResult,
    TableRow,
    register_ocr_adapter,
    register_table_adapter,
)


class CustomLayoutAdapter(LayoutAdapter):
    provider_name = "custom_layout"

    def available(self) -> bool:
        return True

    def parse(self, document: DocumentInput) -> LayoutAdapterResult:
        return LayoutAdapterResult(
            blocks=[
                ParsedLayoutBlock(
                    page=1,
                    text="custom block",
                    bbox=BBox(x0=0, y0=0, x1=10, y1=10),
                    reading_order=1,
                )
            ]
        )


class CustomOCRAdapter(OCRAdapter):
    provider_name = "custom_ocr"

    def available(self) -> bool:
        return True

    def parse(self, document: DocumentInput) -> OCRAdapterResult:
        return OCRAdapterResult(blocks=[OCRTextBlock(page=1, text="ocr text", bbox=BBox(x0=0, y0=0, x1=10, y1=10))])


class CustomTableAdapter(TableAdapter):
    provider_name = "custom_table"

    def available(self) -> bool:
        return True

    def parse(self, document: DocumentInput) -> TableAdapterResult:
        return TableAdapterResult(headers=["h1"], rows=[TableRow(values=["v1"])], bbox=BBox(x0=0, y0=0, x1=10, y1=10), page=1)


def _profile() -> DocumentProfile:
    return DocumentProfile(
        origin_type=OriginType.NATIVE_DIGITAL,
        layout_complexity=LayoutComplexity.TABLE_HEAVY,
        language="en",
        domain_hint=DomainHint.FINANCE,
        extraction_cost=ExtractionCostTier.C_VISION_AUGMENTED,
        confidence=0.9,
        char_count=10,
        char_density=10.0,
        image_ratio=0.2,
        font_metadata_present=True,
        table_marker_count=3,
    )


def test_layout_adapter_registry_supports_custom_provider() -> None:
    register_layout_adapter("acme_layout", lambda: CustomLayoutAdapter())
    adapter = build_layout_adapter("acme_layout")
    parsed = adapter.parse(DocumentInput(document_id="d", source_uri="local://d", content="seed"))

    assert adapter.provider_name == "custom_layout"
    assert parsed.blocks and parsed.blocks[0].text == "custom block"


def test_vision_strategy_uses_configured_custom_vendors() -> None:
    register_ocr_adapter("acme_ocr", lambda: CustomOCRAdapter())
    register_table_adapter("acme_table", lambda: CustomTableAdapter())

    settings = load_settings("configs/settings.yaml")
    settings.extraction.adapters.ocr = "acme_ocr"
    settings.extraction.adapters.table = "acme_table"

    extractor = build_extractor("vision_augmented", settings)
    result = extractor.extract(
        DocumentInput(document_id="d2", source_uri="local://d2", content="a,b\n1,2", mime_type="application/pdf"),
        _profile(),
    )

    assert result.audit
    metadata = result.audit[0].metadata
    assert metadata.get("ocr_provider") == "custom_ocr"
    assert metadata.get("table_provider") == "custom_table"
