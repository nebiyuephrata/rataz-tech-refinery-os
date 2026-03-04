from rataz_tech.core.models import DocumentInput
from rataz_tech.main import build_pipeline


def test_auto_triage_adds_decision_audit() -> None:
    pipeline = build_pipeline("configs/settings.yaml")
    doc = DocumentInput(
        document_id="triage-1",
        source_uri="local://triage-1.txt",
        content="Simple deterministic content",
        mime_type="text/plain",
    )

    result = pipeline.ingest(doc)
    assert any(a.message == "Extraction triage decision" for a in result.extraction.audit)


def test_auto_triage_prefers_table_path_when_markers_high() -> None:
    pipeline = build_pipeline("configs/settings.yaml")
    table_text = "a,b,c\n1,2,3\n" * 8
    doc = DocumentInput(
        document_id="triage-2",
        source_uri="local://triage-2.txt",
        content=table_text,
        mime_type="text/plain",
    )

    result = pipeline.ingest(doc)
    decision = [a for a in result.extraction.audit if a.message == "Extraction triage decision"][0]
    assert decision.metadata["primary"] == "camelot_table"
