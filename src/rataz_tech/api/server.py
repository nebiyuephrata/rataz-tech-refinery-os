from __future__ import annotations

import os
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import Depends, FastAPI, File, UploadFile

from rataz_tech.api.models import ApiErrorResponse, HealthResponse, RequestAuditListResponse, RequestAuditRecord
from rataz_tech.api.services import APIKeyAuthService, FileIngestService, RequestAuditService
from rataz_tech.core.models import DocumentInput, PipelineResult, QueryRequest, QueryResponse
from rataz_tech.main import build_pipeline


def create_app(config_path: str | None = None) -> FastAPI:
    cfg_path = config_path or os.environ.get("RATAZ_TECH_CONFIG", "configs/settings.yaml")
    pipeline = build_pipeline(cfg_path)

    auth = APIKeyAuthService(pipeline.settings.api)
    file_ingest = FileIngestService(pipeline.settings.api)
    audit = RequestAuditService(max_records=pipeline.settings.api.max_audit_records)

    error_responses = {
        401: {"model": ApiErrorResponse},
        413: {"model": ApiErrorResponse},
        415: {"model": ApiErrorResponse},
        422: {"model": ApiErrorResponse},
    }

    app = FastAPI(title="Rataz Tech Refinery-OS API", version="0.2.0")

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", app=pipeline.settings.app.name)

    @app.post("/ingest", response_model=PipelineResult, responses=error_responses)
    def ingest(doc: DocumentInput, _: None = Depends(auth.verify)) -> PipelineResult:
        result = pipeline.ingest(doc)
        audit.add(
            RequestAuditRecord(
                route="/ingest",
                method="POST",
                trace_id=result.trace_id,
                document_id=doc.document_id,
                timestamp_utc=datetime.now(timezone.utc),
            )
        )
        return result

    @app.post("/ingest/file", response_model=PipelineResult, responses=error_responses)
    async def ingest_file(
        file: UploadFile = File(...),
        _: None = Depends(auth.verify),
    ) -> PipelineResult:
        content, mime_type = await file_ingest.read_upload_as_text(file)
        doc_id = f"upload-{uuid4()}"
        source_uri = f"upload://{file.filename or doc_id}"

        result = pipeline.ingest(
            DocumentInput(
                document_id=doc_id,
                source_uri=source_uri,
                content=content,
                mime_type=mime_type,
            )
        )
        audit.add(
            RequestAuditRecord(
                route="/ingest/file",
                method="POST",
                trace_id=result.trace_id,
                document_id=doc_id,
                timestamp_utc=datetime.now(timezone.utc),
            )
        )
        return result

    @app.post("/query", response_model=QueryResponse, responses=error_responses)
    def query(request: QueryRequest, _: None = Depends(auth.verify)) -> QueryResponse:
        response = pipeline.query(request)
        audit.add(
            RequestAuditRecord(
                route="/query",
                method="POST",
                trace_id=response.trace_id,
                timestamp_utc=datetime.now(timezone.utc),
            )
        )
        return response

    @app.get("/audit/requests", response_model=RequestAuditListResponse, responses=error_responses)
    def list_request_audit(_: None = Depends(auth.verify)) -> RequestAuditListResponse:
        return RequestAuditListResponse(records=audit.list())

    return app


app = create_app()


def run_api() -> None:
    import uvicorn

    host = os.environ.get("RATAZ_TECH_API_HOST", "127.0.0.1")
    port = int(os.environ.get("RATAZ_TECH_API_PORT", "8000"))
    uvicorn.run("rataz_tech.api.server:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    run_api()
