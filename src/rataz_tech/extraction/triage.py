from __future__ import annotations

import string
from typing import Iterable

from pydantic import BaseModel, Field

from rataz_tech.core.config import ExtractionConfig
from rataz_tech.core.models import DocumentInput


class ExtractionPlan(BaseModel):
    primary: str
    fallback_chain: list[str] = Field(default_factory=list)
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)


def _printable_ratio(text: str) -> float:
    if not text:
        return 0.0
    printable = set(string.printable)
    printable_count = sum(1 for char in text if char in printable)
    return printable_count / max(1, len(text))


def _table_markers(text: str) -> int:
    return sum(text.count(token) for token in ("|", "\t", ","))


def _without(items: Iterable[str], value: str) -> list[str]:
    return [item for item in items if item != value]


def build_extraction_plan(document: DocumentInput, cfg: ExtractionConfig) -> ExtractionPlan:
    text = document.content or ""
    marker_count = _table_markers(text)
    printable_ratio = _printable_ratio(text)
    looks_pdf = document.mime_type == "application/pdf"

    if printable_ratio < cfg.low_printable_ratio_for_ocr:
        primary = "tesseract_ocr"
        return ExtractionPlan(
            primary=primary,
            fallback_chain=_without(cfg.fallback_chain, primary),
            reason="Low printable ratio indicates OCR-first path",
            confidence=0.85,
        )

    if marker_count >= cfg.min_table_markers_for_table_strategy:
        primary = "camelot_table"
        return ExtractionPlan(
            primary=primary,
            fallback_chain=_without(cfg.fallback_chain, primary),
            reason="Table markers exceed configured threshold",
            confidence=0.8,
        )

    if looks_pdf and cfg.prefer_layout_for_pdf and len(text) >= cfg.min_chars_for_layout:
        primary = "docling_layout"
        return ExtractionPlan(
            primary=primary,
            fallback_chain=_without(cfg.fallback_chain, primary),
            reason="PDF with sufficient size routed to layout-aware extraction",
            confidence=0.78,
        )

    return ExtractionPlan(
        primary=cfg.default_strategy,
        fallback_chain=_without(cfg.fallback_chain, cfg.default_strategy),
        reason="Default deterministic extraction strategy",
        confidence=0.95,
    )
