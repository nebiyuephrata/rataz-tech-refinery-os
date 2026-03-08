from __future__ import annotations

from pydantic import BaseModel, Field

from rataz_tech.core.models import AuditEvent, ClaimVerificationResponse, PageIndexQueryRequest, ProvenanceChain, QueryRequest, StageName, StructuredQueryResponse
from rataz_tech.indexing.facts import extract_numerical_facts, structured_fact_query


class QueryAgentRequest(BaseModel):
    document_id: str
    query: str
    language: str = "en"
    max_results: int = Field(default=5, ge=1, le=50)


class QueryAgentResponse(BaseModel):
    query: str
    tool_used: str
    answer: str
    citations: list[ProvenanceChain] = Field(default_factory=list)
    audit: list[AuditEvent] = Field(default_factory=list)


class QueryAgent:
    def __init__(self, pipeline) -> None:
        self.pipeline = pipeline

    @staticmethod
    def _route_tool(query: str) -> str:
        q = query.lower()
        if any(tok in q for tok in ["go to", "navigate", "section", "where in", "page"]):
            return "pageindex_navigate"
        if any(tok in q for tok in ["how much", "exact", "value", "amount", "number", "sql", "revenue", "ebitda", "profit", "loss", "income"]):
            return "structured_query"
        return "semantic_search"

    def _semantic_search(self, request: QueryAgentRequest) -> QueryAgentResponse:
        response = self.pipeline.query(QueryRequest(query=request.query, language=request.language, max_results=request.max_results))
        citations: list[ProvenanceChain] = []
        for hit in response.hits:
            for prov in hit.provenance:
                page = prov.spatial.page if prov.spatial else 1
                citations.append(
                    ProvenanceChain(
                        document_name=prov.source_uri,
                        page_number=page,
                        content_hash=f"{prov.record_id}-hash",
                    )
                )
        answer = response.hits[0].snippet if response.hits else "No matching evidence found"
        return QueryAgentResponse(query=request.query, tool_used="semantic_search", answer=answer, citations=citations, audit=response.audit)

    def _pageindex_navigate(self, request: QueryAgentRequest) -> QueryAgentResponse:
        response = self.pipeline.query_pageindex(
            PageIndexQueryRequest(document_id=request.document_id, query=request.query, top_k=request.max_results)
        )
        if response.hits:
            best = response.hits[0]
            answer = f"Section: {best.title} (pages {best.page_start}-{best.page_end})"
            citations = best.provenance
        else:
            answer = "No matching section found"
            citations = []
        return QueryAgentResponse(query=request.query, tool_used="pageindex_navigate", answer=answer, citations=citations, audit=response.audit)

    def _structured_query(self, request: QueryAgentRequest) -> QueryAgentResponse:
        result = self.pipeline.get_latest_result(request.document_id)
        if result is None:
            return QueryAgentResponse(
                query=request.query,
                tool_used="structured_query",
                answer="No document found for structured query",
                citations=[],
                audit=[AuditEvent(stage=StageName.QUERYING, message="Structured query skipped: missing document")],
            )

        rows = structured_fact_query(extract_numerical_facts(result), request.query, limit=request.max_results)
        if rows:
            answer = "; ".join(f"{r.metric}={r.value}" for r in rows)
            citations = [
                ProvenanceChain(
                    document_name=request.document_id,
                    page_number=r.page_number,
                    content_hash=r.content_hash,
                )
                for r in rows
            ]
        else:
            answer = "No numerical fact matched the query"
            citations = []

        sq = StructuredQueryResponse(
            document_id=request.document_id,
            query=request.query,
            rows=rows,
            audit=[AuditEvent(stage=StageName.QUERYING, message="Structured query executed", metadata={"rows": str(len(rows))})],
        )
        return QueryAgentResponse(query=request.query, tool_used="structured_query", answer=answer, citations=citations, audit=sq.audit)

    def verify_claim(self, document_id: str, claim: str) -> ClaimVerificationResponse:
        result = self.pipeline.get_latest_result(document_id)
        if result is None:
            return ClaimVerificationResponse(
                document_id=document_id,
                claim=claim,
                verified=False,
                status="not_found",
                audit=[AuditEvent(stage=StageName.QUERYING, message="Claim verification failed: document missing")],
            )

        claim_lower = claim.lower()
        for unit in result.extraction.units:
            if claim_lower in (unit.text or "").lower():
                page = unit.provenance.spatial.page if unit.provenance.spatial else 1
                citation = ProvenanceChain(
                    document_name=unit.provenance.source_uri,
                    page_number=page,
                    content_hash=f"{unit.unit_id}-hash",
                )
                return ClaimVerificationResponse(
                    document_id=document_id,
                    claim=claim,
                    verified=True,
                    status="verified",
                    citation=citation,
                    audit=[AuditEvent(stage=StageName.QUERYING, message="Claim verified")],
                )

        return ClaimVerificationResponse(
            document_id=document_id,
            claim=claim,
            verified=False,
            status="unverifiable",
            audit=[AuditEvent(stage=StageName.QUERYING, message="Claim not found in evidence")],
        )

    def answer(self, request: QueryAgentRequest) -> QueryAgentResponse:
        tool = self._route_tool(request.query)
        if tool == "pageindex_navigate":
            return self._pageindex_navigate(request)
        if tool == "structured_query":
            return self._structured_query(request)
        return self._semantic_search(request)
