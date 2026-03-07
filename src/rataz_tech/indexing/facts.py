from __future__ import annotations

import hashlib
import re

from rataz_tech.core.models import NumericalFact, PipelineResult


_FACT_RE = re.compile(r"(?P<metric>[A-Za-z][A-Za-z\s_-]{1,40})\s*(?:is|was|=|:)\s*\$?(?P<value>\d+(?:,\d{3})*(?:\.\d+)?)", re.IGNORECASE)


def extract_numerical_facts(result: PipelineResult) -> list[NumericalFact]:
    facts: list[NumericalFact] = []
    doc_id = result.extraction.document_id

    for unit in result.extraction.units:
        text = unit.text or ""
        page = unit.provenance.spatial.page if unit.provenance.spatial else 1
        for match in _FACT_RE.finditer(text):
            metric = " ".join(match.group("metric").split()).lower()
            raw = match.group("value").replace(",", "")
            value = float(raw)
            facts.append(
                NumericalFact(
                    document_id=doc_id,
                    metric=metric,
                    value=value,
                    unit="usd" if "$" in match.group(0) else "",
                    page_number=page,
                    content_hash=hashlib.sha256(match.group(0).encode("utf-8", errors="ignore")).hexdigest(),
                    source_text=match.group(0),
                )
            )

    extracted_doc = result.extraction.extracted_document
    if extracted_doc:
        for table in extracted_doc.tables:
            for row in table.rows:
                for i, cell in enumerate(row):
                    cell_clean = cell.replace(",", "")
                    if not re.fullmatch(r"\d+(?:\.\d+)?", cell_clean):
                        continue
                    metric = table.headers[i].strip().lower() if i < len(table.headers) else f"col_{i}"
                    facts.append(
                        NumericalFact(
                            document_id=doc_id,
                            metric=metric,
                            value=float(cell_clean),
                            unit="",
                            page_number=table.page_number,
                            content_hash=hashlib.sha256(f"{metric}:{cell_clean}".encode("utf-8", errors="ignore")).hexdigest(),
                            source_text=f"{metric}: {cell}",
                        )
                    )

    # Deterministic deduplication by (metric, value, page)
    dedup: dict[tuple[str, float, int], NumericalFact] = {}
    for fact in facts:
        dedup[(fact.metric, fact.value, fact.page_number)] = fact
    return list(dedup.values())


def structured_fact_query(facts: list[NumericalFact], query: str, limit: int = 5) -> list[NumericalFact]:
    q = query.lower()
    ranked = sorted(
        facts,
        key=lambda f: (
            1 if f.metric in q else 0,
            sum(1 for tok in f.metric.split() if tok in q),
        ),
        reverse=True,
    )
    return [f for f in ranked if f.metric in q or any(tok in q for tok in f.metric.split())][:limit]
