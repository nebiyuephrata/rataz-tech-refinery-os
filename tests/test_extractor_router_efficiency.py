from __future__ import annotations

from rataz_tech.core.config import load_settings
from rataz_tech.core.models import DocumentInput, DocumentProfile
import rataz_tech.extraction.factory as factory_module
from rataz_tech.extraction.factory import AutoTriageExtractionStrategy
from rataz_tech.extraction.strategies import ExtractionStrategy


class FakeStrategy(ExtractionStrategy):
    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def strategy_name(self) -> str:
        return self._name

    @property
    def tier_name(self) -> str:
        return "A_fast_text"

    def extract(self, document: DocumentInput, profile: DocumentProfile | None = None):
        from rataz_tech.core.models import AuditEvent, ExtractionResult, ExtractedUnit, ProvenanceRecord, SpatialProvenance, StageName

        prov = ProvenanceRecord(
            source_uri=document.source_uri,
            extractor=self._name,
            record_id="r",
            confidence=1.0,
            spatial=SpatialProvenance(page=1, x0=0, y0=0, x1=1, y1=1),
        )
        return ExtractionResult(
            document_id=document.document_id,
            profile=profile,
            strategy_used=self._name,
            strategy_confidence=1.0,
            units=[ExtractedUnit(unit_id="u", text=document.content, provenance=prov)],
            audit=[AuditEvent(stage=StageName.EXTRACTION, message="ok")],
        )


def test_auto_triage_reuses_strategy_instances(monkeypatch) -> None:
    settings = load_settings("configs/settings.yaml")
    router = AutoTriageExtractionStrategy(settings)

    created = {"count": 0}

    def _fake_strategy_builder(name: str, settings):
        created["count"] += 1
        return FakeStrategy(name)

    monkeypatch.setattr(factory_module, "_strategy_by_name", _fake_strategy_builder)

    doc = DocumentInput(document_id="d", source_uri="local://d", content="alpha", mime_type="text/plain")
    router.extract(doc)
    router.extract(doc)

    assert created["count"] == 1
