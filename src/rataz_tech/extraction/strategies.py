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


class OCREmulationAdapter(ExtractionStrategy):
    """Adapter placeholder for future OCR engines while keeping a stable contract."""

    def __init__(self, wrapped: ExtractionStrategy) -> None:
        self._wrapped = wrapped

    def extract(self, document: DocumentInput) -> ExtractionResult:
        result = self._wrapped.extract(document)
        result.audit.append(
            AuditEvent(
                stage=StageName.EXTRACTION,
                message="OCR adapter pass-through used (deterministic fallback)",
                metadata={"adapter": "ocr_emulation"},
            )
        )
        return result
