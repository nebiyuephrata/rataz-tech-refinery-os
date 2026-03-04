from __future__ import annotations

from abc import ABC, abstractmethod
import re

from rataz_tech.core.models import (
    AuditEvent,
    ExtractionResult,
    NormalizationResult,
    NormalizedUnit,
    StageName,
)


class NormalizationStrategy(ABC):
    @abstractmethod
    def normalize(self, extraction: ExtractionResult) -> NormalizationResult:
        raise NotImplementedError


class RuleBasedNormalizationStrategy(NormalizationStrategy):
    MULTISPACE = re.compile(r"\s+")

    def normalize(self, extraction: ExtractionResult) -> NormalizationResult:
        units = []
        for unit in extraction.units:
            text = unit.text.strip().lower()
            text = self.MULTISPACE.sub(" ", text)
            units.append(
                NormalizedUnit(
                    unit_id=unit.unit_id,
                    normalized_text=text,
                    provenance=unit.provenance,
                )
            )
        return NormalizationResult(
            document_id=extraction.document_id,
            units=units,
            audit=[AuditEvent(stage=StageName.NORMALIZATION, message="Rule-based normalization applied")],
        )
