from __future__ import annotations

import yaml

from rataz_tech.core.models import DocumentInput
from rataz_tech.main import build_pipeline


def test_auto_triage_adds_decision_audit_with_profile_fields() -> None:
    pipeline = build_pipeline("configs/settings.yaml")
    doc = DocumentInput(
        document_id="triage-1",
        source_uri="local://triage-1.txt",
        content="This assessment rubric score and evaluation are traceable.",
        mime_type="text/plain",
    )

    result = pipeline.ingest(doc)
    assert result.extraction.profile is not None
    assert result.extraction.profile.domain_hint.value in {"assessment", "general"}

    decision = [a for a in result.extraction.audit if a.message == "Extraction triage decision"][0]
    assert "initial_tier" in decision.metadata
    assert "strategy_selected" in decision.metadata


def test_auto_triage_table_heavy_routes_to_layout_tier() -> None:
    pipeline = build_pipeline("configs/settings.yaml")
    table_text = "a,b,c\n1,2,3\n" * 12
    doc = DocumentInput(
        document_id="triage-2",
        source_uri="local://triage-2.txt",
        content=table_text,
        mime_type="text/plain",
    )

    result = pipeline.ingest(doc)
    assert result.extraction.profile is not None
    assert result.extraction.profile.layout_complexity.value in {"table_heavy", "mixed"}
    assert "B_layout_aware" in result.extraction.escalation_path or "C_vision_augmented" in result.extraction.escalation_path


def test_router_escalates_to_vision_when_thresholds_force_retry(tmp_path) -> None:
    with open("configs/settings.yaml", "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)

    cfg["extraction"]["strategy_confidence_thresholds"]["A_fast_text"] = 0.99
    cfg["extraction"]["strategy_confidence_thresholds"]["B_layout_aware"] = 0.99
    cfg_path = tmp_path / "settings-escalation.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg), encoding="utf-8")

    pipeline = build_pipeline(str(cfg_path))
    result = pipeline.ingest(
        DocumentInput(
            document_id="triage-3",
            source_uri="local://triage-3.txt",
            content="Simple text document to force escalation for rubric test.",
            mime_type="text/plain",
        )
    )

    assert result.extraction.escalation_path[:2] == ["A_fast_text", "B_layout_aware"]
    assert result.extraction.strategy_used in {"vision_augmented", "tesseract_ocr"}
