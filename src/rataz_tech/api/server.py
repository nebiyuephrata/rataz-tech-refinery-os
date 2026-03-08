from __future__ import annotations

import os
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from rataz_tech.api.models import (
    ApiErrorResponse,
    HealthResponse,
    RequestAuditListResponse,
    RequestAuditRecord,
    StoredExtractionResponse,
    StoredPageIndexResponse,
)
from rataz_tech.api.services import APIKeyAuthService, FileIngestService, build_request_store
from rataz_tech.core.models import (
    ClaimVerificationRequest,
    ClaimVerificationResponse,
    DocumentInput,
    PageIndexQueryRequest,
    PageIndexQueryResponse,
    PipelineResult,
    QueryRequest,
    QueryResponse,
    StructuredQueryRequest,
    StructuredQueryResponse,
)
from rataz_tech.main import build_pipeline
from rataz_tech.querying.agent import QueryAgent, QueryAgentRequest, QueryAgentResponse


def create_app(config_path: str | None = None) -> FastAPI:
    cfg_path = config_path or os.environ.get("RATAZ_TECH_CONFIG", "configs/settings.yaml")
    pipeline = build_pipeline(cfg_path)

    auth = APIKeyAuthService(pipeline.settings.api)
    file_ingest = FileIngestService(pipeline.settings.api)
    store = build_request_store(pipeline.settings.storage, pipeline.settings.api)
    query_agent = QueryAgent(pipeline)

    error_responses = {
        401: {"model": ApiErrorResponse},
        404: {"model": ApiErrorResponse},
        413: {"model": ApiErrorResponse},
        415: {"model": ApiErrorResponse},
        422: {"model": ApiErrorResponse},
    }

    app = FastAPI(title="Rataz Tech Refinery-OS API", version="0.3.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=pipeline.settings.api.cors_allow_origins,
        allow_methods=pipeline.settings.api.cors_allow_methods,
        allow_headers=pipeline.settings.api.cors_allow_headers,
    )

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            app=pipeline.settings.app.name,
            storage_backend=pipeline.settings.storage.backend,
        )

    @app.post("/ingest", response_model=PipelineResult, responses=error_responses)
    def ingest(doc: DocumentInput, _: None = Depends(auth.verify)) -> PipelineResult:
        result = pipeline.ingest(doc)
        store.save_extraction(result)
        built = pipeline.get_pageindex(doc.document_id)
        if built is not None:
            store.save_pageindex(built)
        store.add_audit(
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
        store.save_extraction(result)
        built = pipeline.get_pageindex(doc_id)
        if built is not None:
            store.save_pageindex(built)
        store.add_audit(
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
        store.add_audit(
            RequestAuditRecord(
                route="/query",
                method="POST",
                trace_id=response.trace_id,
                timestamp_utc=datetime.now(timezone.utc),
            )
        )
        return response

    @app.post("/query/structured", response_model=StructuredQueryResponse, responses=error_responses)
    def query_structured(request: StructuredQueryRequest, _: None = Depends(auth.verify)) -> StructuredQueryResponse:
        response = store.structured_query(request.document_id, request.query, request.limit)
        store.add_audit(
            RequestAuditRecord(
                route="/query/structured",
                method="POST",
                trace_id=f"structured-{uuid4()}",
                document_id=request.document_id,
                timestamp_utc=datetime.now(timezone.utc),
            )
        )
        return response

    @app.post("/query/agent", response_model=QueryAgentResponse, responses=error_responses)
    def query_agent_endpoint(request: QueryAgentRequest, _: None = Depends(auth.verify)) -> QueryAgentResponse:
        response = query_agent.answer(request)
        store.add_audit(
            RequestAuditRecord(
                route="/query/agent",
                method="POST",
                trace_id=f"agent-{uuid4()}",
                document_id=request.document_id,
                timestamp_utc=datetime.now(timezone.utc),
            )
        )
        return response

    @app.post("/audit/claim", response_model=ClaimVerificationResponse, responses=error_responses)
    def verify_claim(request: ClaimVerificationRequest, _: None = Depends(auth.verify)) -> ClaimVerificationResponse:
        response = store.verify_claim(request.document_id, request.claim)
        store.add_audit(
            RequestAuditRecord(
                route="/audit/claim",
                method="POST",
                trace_id=f"claim-{uuid4()}",
                document_id=request.document_id,
                timestamp_utc=datetime.now(timezone.utc),
            )
        )
        return response

    @app.get("/audit/requests", response_model=RequestAuditListResponse, responses=error_responses)
    def list_request_audit(
        _: None = Depends(auth.verify),
        limit: int = Query(default=100, ge=1, le=1000),
        route: str | None = Query(default=None),
        document_id: str | None = Query(default=None),
    ) -> RequestAuditListResponse:
        return RequestAuditListResponse(records=store.list_audit(limit=limit, route=route, document_id=document_id))

    @app.get("/extractions/{document_id}", response_model=StoredExtractionResponse, responses=error_responses)
    def get_extraction(document_id: str, _: None = Depends(auth.verify)) -> StoredExtractionResponse:
        item = store.get_latest_extraction(document_id)
        if item is None:
            raise HTTPException(status_code=404, detail=f"No extraction found for document_id={document_id}")
        return item

    @app.get("/pageindex/{document_id}", response_model=StoredPageIndexResponse, responses=error_responses)
    def get_pageindex(document_id: str, _: None = Depends(auth.verify)) -> StoredPageIndexResponse:
        item = store.get_pageindex(document_id)
        if item is None:
            raise HTTPException(status_code=404, detail=f"No page index found for document_id={document_id}")
        return item

    @app.post("/pageindex/query", response_model=PageIndexQueryResponse, responses=error_responses)
    def query_pageindex(request: PageIndexQueryRequest, _: None = Depends(auth.verify)) -> PageIndexQueryResponse:
        response = pipeline.query_pageindex(request)
        store.add_audit(
            RequestAuditRecord(
                route="/pageindex/query",
                method="POST",
                trace_id=response.trace_id,
                document_id=request.document_id,
                timestamp_utc=datetime.now(timezone.utc),
            )
        )
        return response

    return app


app = create_app()


def run_api() -> None:
    import uvicorn

    host = os.environ.get("RATAZ_TECH_API_HOST", "127.0.0.1")
    port = int(os.environ.get("RATAZ_TECH_API_PORT", "8000"))
    uvicorn.run("rataz_tech.api.server:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    run_api()
