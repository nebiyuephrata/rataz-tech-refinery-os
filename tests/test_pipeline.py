from rataz_tech.core.models import DocumentInput, QueryRequest
from rataz_tech.main import build_pipeline


def test_pipeline_end_to_end() -> None:
    pipeline = build_pipeline("configs/settings.yaml")
    result = pipeline.ingest(
        DocumentInput(
            document_id="d1",
            source_uri="local://d1.txt",
            content="Alpha beta gamma provenance token",
        )
    )

    assert result.extraction.units
    assert result.chunking.chunks
    assert result.chunking.chunks[0].provenance

    resp = pipeline.query(QueryRequest(query="provenance", language="en", max_results=3))
    assert isinstance(resp.model_dump(), dict)
    assert resp.hits


def test_amharic_localization_for_no_hits() -> None:
    pipeline = build_pipeline("configs/settings.yaml")
    pipeline.ingest(
        DocumentInput(
            document_id="d2",
            source_uri="local://d2.txt",
            content="deterministic indexing test",
        )
    )

    resp = pipeline.query(QueryRequest(query="does-not-exist", language="am", max_results=2))
    assert resp.reason == "ተመሳሳይ ይዘት አልተገኘም"
