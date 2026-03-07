from __future__ import annotations

from rataz_tech.core.models import DocumentInput
from rataz_tech.extraction.strategies import FastTextExtractionStrategy
from rataz_tech.extraction.pdf_parsers import resolve_source_path


def test_resolve_source_path() -> None:
    assert resolve_source_path("file:///tmp/a.pdf") == "/tmp/a.pdf"
    assert resolve_source_path("local:///tmp/a.pdf") == "/tmp/a.pdf"
    assert resolve_source_path("http://example.com/a.pdf") is None


def test_fast_text_parser_metadata_present() -> None:
    strategy = FastTextExtractionStrategy()
    result = strategy.extract(
        DocumentInput(
            document_id="parser-1",
            source_uri="local://not-real.pdf",
            content="fallback text",
            mime_type="application/pdf",
        )
    )

    fast_events = [a for a in result.audit if a.message == "Fast text extraction completed"]
    assert fast_events
    assert "parser" in fast_events[0].metadata
