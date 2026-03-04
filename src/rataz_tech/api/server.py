from __future__ import annotations

import os

from fastapi import FastAPI

from rataz_tech.core.models import DocumentInput, PipelineResult, QueryRequest, QueryResponse
from rataz_tech.main import build_pipeline


def _build_app() -> FastAPI:
    config_path = os.environ.get("RATAZ_TECH_CONFIG", "configs/settings.yaml")
    pipeline = build_pipeline(config_path)

    app = FastAPI(title="Rataz Tech Refinery-OS API", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/ingest", response_model=PipelineResult)
    def ingest(doc: DocumentInput) -> PipelineResult:
        return pipeline.ingest(doc)

    @app.post("/query", response_model=QueryResponse)
    def query(request: QueryRequest) -> QueryResponse:
        return pipeline.query(request)

    return app


app = _build_app()


def run_api() -> None:
    import uvicorn

    host = os.environ.get("RATAZ_TECH_API_HOST", "127.0.0.1")
    port = int(os.environ.get("RATAZ_TECH_API_PORT", "8000"))
    uvicorn.run("rataz_tech.api.server:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    run_api()
