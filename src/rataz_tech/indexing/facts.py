from __future__ import annotations

import hashlib
import re

from rataz_tech.core.models import NumericalFact, PipelineResult


_FACT_RE = re.compile(r"(?P<metric>[A-Za-z][A-Za-z\s_-]{1,40})\s*(?:is|was|=|:)\s*\$?(?P<value>\d+(?:,\d{3})*(?:\.\d+)?)", re.IGNORECASE)
_LINE_VALUE_RE = re.compile(r"\(?-?\d{1,3}(?:,\d{3})*(?:\.\d+)?\)?")
_FIN_KEYWORD_RE = re.compile(r"\b(profit|loss|revenue|income|expense|ebitda|ebit)\b", re.IGNORECASE)


def _to_float(raw: str) -> float | None:
    cleaned = raw.strip()
    negative = cleaned.startswith("(") and cleaned.endswith(")")
    cleaned = cleaned.strip("()").replace(",", "")
    try:
        value = float(cleaned)
    except ValueError:
        return None
    return -value if negative else value


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
        # OCR-friendly line parsing for financial statements where values are inline without 'is/was'.
        for line in text.splitlines():
            line_clean = " ".join(line.split())
            if not line_clean or not _FIN_KEYWORD_RE.search(line_clean):
                continue
            values = _LINE_VALUE_RE.findall(line_clean)
            if not values:
                continue
            raw_value = values[-1]
            value = _to_float(raw_value)
            if value is None:
                continue
            metric = _LINE_VALUE_RE.sub("", line_clean).strip(" :.-").lower()
            if len(metric) < 3:
                continue
            facts.append(
                NumericalFact(
                    document_id=doc_id,
                    metric=metric,
                    value=value,
                    unit="usd" if "$" in line_clean else "",
                    page_number=page,
                    content_hash=hashlib.sha256(line_clean.encode("utf-8", errors="ignore")).hexdigest(),
                    source_text=line_clean,
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
