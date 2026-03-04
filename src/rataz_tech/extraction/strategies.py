from __future__ import annotations

from abc import ABC, abstractmethod

from rataz_tech.core.models import (
    AuditEvent,
    DocumentInput,
    ExtractionResult,
    ExtractedUnit,
    ProvenanceRecord,
    SpatialProvenance,
    StageName,
)


class ExtractionStrategy(ABC):
    @abstractmethod
    def extract(self, document: DocumentInput) -> ExtractionResult:
        raise NotImplementedError


class PlainTextExtractionStrategy(ExtractionStrategy):
    def extract(self, document: DocumentInput) -> ExtractionResult:
        prov = ProvenanceRecord(
            source_uri=document.source_uri,
            extractor="plain_text",
            record_id=f"{document.document_id}:u0",
            confidence=1.0,
            spatial=SpatialProvenance(page=1, x0=0, y0=0, x1=1, y1=1),
        )
        unit = ExtractedUnit(unit_id=f"{document.document_id}:u0", text=document.content, provenance=prov)
        return ExtractionResult(
            document_id=document.document_id,
            units=[unit],
            audit=[
                AuditEvent(
                    stage=StageName.EXTRACTION,
                    message="Document extracted with plain text strategy",
                    metadata={"mime_type": document.mime_type},
                )
            ],
        )


class FallbackAdapter(ExtractionStrategy):
    """Adapter that records fallback behavior if optional tool backends are unavailable."""

    adapter_name: str = "fallback"

    def __init__(self, wrapped: ExtractionStrategy) -> None:
        self._wrapped = wrapped

    def _tool_available(self) -> bool:
        return False

    def extract(self, document: DocumentInput) -> ExtractionResult:
        result = self._wrapped.extract(document)
        available = self._tool_available()
        result.audit.append(
            AuditEvent(
                stage=StageName.EXTRACTION,
                message=f"{self.adapter_name} adapter {'active' if available else 'fallback'}",
                metadata={"adapter": self.adapter_name, "available": str(available).lower()},
            )
        )
        return result


class OCRFallbackAdapter(FallbackAdapter):
    adapter_name = "ocr_emulation"


class PdfPlumberAdapter(FallbackAdapter):
    adapter_name = "pdfplumber_text"

    def _tool_available(self) -> bool:
        try:
            import pdfplumber  # noqa: F401

            return True
        except ImportError:
            return False


class PyMuPDFAdapter(FallbackAdapter):
    adapter_name = "pymupdf_text"

    def _tool_available(self) -> bool:
        try:
            import fitz  # noqa: F401

            return True
        except ImportError:
            return False


class DoclingLayoutAdapter(FallbackAdapter):
    adapter_name = "docling_layout"

    def _tool_available(self) -> bool:
        try:
            import docling  # noqa: F401

            return True
        except ImportError:
            return False


class MinerULayoutAdapter(FallbackAdapter):
    adapter_name = "mineru_layout"

    def _tool_available(self) -> bool:
        try:
            import mineru  # noqa: F401

            return True
        except ImportError:
            return False


class TesseractOCRAdapter(FallbackAdapter):
    adapter_name = "tesseract_ocr"

    def _tool_available(self) -> bool:
        try:
            import pytesseract  # noqa: F401

            return True
        except ImportError:
            return False


class CamelotTableAdapter(FallbackAdapter):
    adapter_name = "camelot_table"

    def _tool_available(self) -> bool:
        try:
            import camelot  # noqa: F401

            return True
        except ImportError:
            return False


# Backward-compatible alias for previous code paths.
OCREmulationAdapter = OCRFallbackAdapter
