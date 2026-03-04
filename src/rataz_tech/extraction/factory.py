from __future__ import annotations

from rataz_tech.core.config import Settings
from rataz_tech.core.models import DocumentInput
from rataz_tech.extraction.strategies import (
    CamelotTableAdapter,
    DoclingLayoutAdapter,
    ExtractionStrategy,
    MinerULayoutAdapter,
    OCRFallbackAdapter,
    PdfPlumberAdapter,
    PlainTextExtractionStrategy,
    PyMuPDFAdapter,
    TesseractOCRAdapter,
)
from rataz_tech.extraction.triage import build_extraction_plan


def _strategy_by_name(name: str) -> ExtractionStrategy:
    base = PlainTextExtractionStrategy()
    strategies: dict[str, ExtractionStrategy] = {
        "plain_text": base,
        "ocr_adapter": OCRFallbackAdapter(base),
        "pdfplumber_text": PdfPlumberAdapter(base),
        "pymupdf_text": PyMuPDFAdapter(base),
        "docling_layout": DoclingLayoutAdapter(base),
        "mineru_layout": MinerULayoutAdapter(base),
        "tesseract_ocr": TesseractOCRAdapter(base),
        "camelot_table": CamelotTableAdapter(base),
    }
    if name not in strategies:
        raise ValueError(f"Unknown extractor strategy: {name}")
    return strategies[name]


class AutoTriageExtractionStrategy(ExtractionStrategy):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def extract(self, document: DocumentInput):
        plan = build_extraction_plan(document, self._settings.extraction)
        primary = _strategy_by_name(plan.primary)
        result = primary.extract(document)
        result.audit.append(
            result.audit[0].model_copy(
                update={
                    "message": "Extraction triage decision",
                    "metadata": {
                        "primary": plan.primary,
                        "fallback_chain": ",".join(plan.fallback_chain),
                        "reason": plan.reason,
                        "confidence": f"{plan.confidence:.2f}",
                    },
                }
            )
        )
        return result


def build_extractor(name: str, settings: Settings) -> ExtractionStrategy:
    if name == "auto_triage":
        return AutoTriageExtractionStrategy(settings)
    return _strategy_by_name(name)
