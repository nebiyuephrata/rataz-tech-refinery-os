from __future__ import annotations

from rataz_tech.core.models import DocumentInput
from rataz_tech.main import build_pipeline
from rataz_tech.querying.agent import QueryAgent, QueryAgentRequest


def test_query_agent_routes_tools_and_returns_citations() -> None:
    pipeline = build_pipeline("configs/settings.yaml")
    pipeline.ingest(
        DocumentInput(
            document_id="qa-doc-1",
            source_uri="local://qa-doc-1.txt",
            content="Revenue was 4200 in Q3. See Section Revenue.",
            mime_type="text/plain",
        )
    )

    agent = QueryAgent(pipeline)
    nav = agent.answer(QueryAgentRequest(document_id="qa-doc-1", query="go to revenue section"))
    sem = agent.answer(QueryAgentRequest(document_id="qa-doc-1", query="what is revenue"))

    assert nav.tool_used == "pageindex_navigate"
    assert sem.tool_used in {"semantic_search", "structured_query"}
    assert sem.citations
