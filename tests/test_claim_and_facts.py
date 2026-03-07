from __future__ import annotations

from rataz_tech.core.models import DocumentInput
from rataz_tech.indexing.facts import extract_numerical_facts, structured_fact_query
from rataz_tech.main import build_pipeline
from rataz_tech.querying.agent import QueryAgent


def test_fact_extraction_and_claim_verification() -> None:
    pipeline = build_pipeline("configs/settings.yaml")
    pipeline.ingest(
        DocumentInput(
            document_id="fact-1",
            source_uri="local://fact-1.txt",
            content="Revenue was $4200 in Q3. EBITDA was 900.",
            mime_type="text/plain",
        )
    )

    result = pipeline.get_latest_result("fact-1")
    assert result is not None
    facts = extract_numerical_facts(result)
    assert facts
    rows = structured_fact_query(facts, "revenue", limit=2)
    assert rows

    agent = QueryAgent(pipeline)
    claim = agent.verify_claim("fact-1", "Revenue was $4200 in Q3")
    assert claim.verified is True
    assert claim.citation is not None
