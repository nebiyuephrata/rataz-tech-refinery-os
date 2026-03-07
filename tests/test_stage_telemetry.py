from __future__ import annotations

from rataz_tech.core.models import DocumentInput, QueryRequest
from rataz_tech.main import build_pipeline


def test_ingest_and_query_emit_stage_telemetry() -> None:
    pipeline = build_pipeline("configs/settings.yaml")
    result = pipeline.ingest(
        DocumentInput(document_id="tele-1", source_uri="local://tele-1.txt", content="Revenue was 4200.", mime_type="text/plain")
    )

    ext_telemetry = [a for a in result.extraction.audit if a.message == "Stage telemetry"]
    idx_telemetry = [a for a in result.indexing.audit if a.message == "Stage telemetry"]
    assert ext_telemetry
    assert idx_telemetry
    assert "duration_ms" in ext_telemetry[0].metadata

    resp = pipeline.query(QueryRequest(query="revenue", language="en", max_results=3))
    q_telemetry = [a for a in resp.audit if a.message == "Stage telemetry"]
    assert q_telemetry
    assert q_telemetry[0].metadata.get("stage") == "querying"
