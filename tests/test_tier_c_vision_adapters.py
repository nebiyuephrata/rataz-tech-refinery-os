from __future__ import annotations

from rataz_tech.core.config import VisionBudgetConfig
from rataz_tech.core.models import (
    BBox,
    DocumentInput,
    DocumentProfile,
    DomainHint,
    ExtractionCostTier,
    LayoutComplexity,
    OriginType,
)
from rataz_tech.extraction.ocr_adapters import OCRAdapterResult, OCRTextBlock, TableAdapterResult, TableRow
from rataz_tech.extraction.strategies import VisionAugmentedExtractionStrategy


class FakeOCRAdapter:
    provider_name = "fake_ocr"

    def available(self) -> bool:
        return True

    def parse(self, document: DocumentInput) -> OCRAdapterResult:
        return OCRAdapterResult(
            blocks=[
                OCRTextBlock(page=1, text="Scanned legal clause", bbox=BBox(x0=0, y0=0, x1=100, y1=20)),
            ]
        )


class FakeTableAdapter:
    provider_name = "fake_table"

    def available(self) -> bool:
        return True

    def parse(self, document: DocumentInput) -> TableAdapterResult:
        return TableAdapterResult(
            headers=["c1", "c2"],
            rows=[TableRow(values=["v1", "v2"])],
            bbox=BBox(x0=0, y0=21, x1=100, y1=40),
            page=1,
        )


def _profile() -> DocumentProfile:
    return DocumentProfile(
        origin_type=OriginType.SCANNED_IMAGE,
        layout_complexity=LayoutComplexity.TABLE_HEAVY,
        language="en",
        domain_hint=DomainHint.LEGAL,
        extraction_cost=ExtractionCostTier.C_VISION_AUGMENTED,
        confidence=0.8,
        char_count=100,
        char_density=20.0,
        image_ratio=0.8,
        font_metadata_present=False,
        table_marker_count=0,
        zero_text=True,
    )


def test_vision_strategy_maps_ocr_and_table_outputs() -> None:
    strategy = VisionAugmentedExtractionStrategy(
        budget=VisionBudgetConfig(max_tokens_per_document=5000, max_cost_usd_per_document=1.0, estimated_cost_per_1k_tokens_usd=0.01),
        tool_name="vision_augmented",
        ocr_adapter=FakeOCRAdapter(),
        table_adapter=FakeTableAdapter(),
    )
    result = strategy.extract(DocumentInput(document_id="v1", source_uri="local://scan.pdf", content="img", mime_type="application/pdf"), _profile())

    assert result.extracted_document is not None
    assert result.extracted_document.text_blocks
    assert result.extracted_document.tables
    assert any(a.metadata.get("ocr_provider") == "fake_ocr" for a in result.audit)
    assert any(a.metadata.get("table_provider") == "fake_table" for a in result.audit)


def test_vision_budget_stop_skips_vendor_calls() -> None:
    class CallCountingAdapter(FakeOCRAdapter):
        def __init__(self) -> None:
            self.called = 0

        def parse(self, document: DocumentInput) -> OCRAdapterResult:
            self.called += 1
            return super().parse(document)

    ocr = CallCountingAdapter()
    strategy = VisionAugmentedExtractionStrategy(
        budget=VisionBudgetConfig(max_tokens_per_document=1, max_cost_usd_per_document=0.00001, estimated_cost_per_1k_tokens_usd=1.0),
        tool_name="vision_augmented",
        ocr_adapter=ocr,
        table_adapter=FakeTableAdapter(),
    )

    result = strategy.extract(
        DocumentInput(document_id="v2", source_uri="local://scan.pdf", content="this is large enough to exceed budget", mime_type="application/pdf"),
        _profile(),
    )

    assert result.review_required is True
    assert ocr.called == 0
