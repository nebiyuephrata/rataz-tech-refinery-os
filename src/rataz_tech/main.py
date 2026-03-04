from __future__ import annotations

from pathlib import Path

from rataz_tech.core.config import load_settings
from rataz_tech.core.models import DocumentInput, QueryRequest
from rataz_tech.orchestration.pipeline import RefineryPipeline


def build_pipeline(config_path: str | Path = "configs/settings.yaml") -> RefineryPipeline:
    settings = load_settings(config_path)
    locale_dir = Path(__file__).parent / "localization" / "locales"
    return RefineryPipeline(settings=settings, locale_dir=locale_dir)


def run_demo() -> None:
    pipeline = build_pipeline()
    doc = DocumentInput(
        document_id="doc-001",
        source_uri="local://demo.txt",
        content="Rataz Tech builds open source document intelligence with spatial provenance.",
    )
    pipeline.ingest(doc)

    resp = pipeline.query(QueryRequest(query="spatial provenance", language="am", max_results=3))
    print(resp.model_dump_json(indent=2, ensure_ascii=False))


if __name__ == "__main__":
    run_demo()
