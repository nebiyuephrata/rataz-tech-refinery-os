from __future__ import annotations

from rataz_tech.core.models import DocumentInput
from rataz_tech.indexing.facts import extract_numerical_facts, structured_fact_query
from rataz_tech.main import build_pipeline


def test_profit_line_fact_extraction_from_ocr_style_text() -> None:
    pipeline = build_pipeline("configs/settings.yaml")
    content = """
Statement of profit or loss
Profit before tax 12,345
Net profit for the year 9,876
Revenue 100,000
"""
    result = pipeline.ingest(
        DocumentInput(
            document_id="profit-line-1",
            source_uri="local://profit-line-1.txt",
            content=content,
            mime_type="text/plain",
        )
    )

    facts = extract_numerical_facts(result)
    assert any("profit" in f.metric for f in facts)

    rows = structured_fact_query(facts, "profit", limit=5)
    assert rows
    assert any("profit" in r.metric for r in rows)
