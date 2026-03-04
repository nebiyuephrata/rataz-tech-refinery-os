from __future__ import annotations

import string

from pydantic import BaseModel, Field

from rataz_tech.core.config import ExtractionConfig
from rataz_tech.core.models import (
    DocumentInput,
    DocumentProfile,
    ExtractionCostTier,
    LayoutComplexity,
    OriginType,
)
from rataz_tech.extraction.domain_classifier import DomainHintClassifier, KeywordDomainHintClassifier


class TriageDecision(BaseModel):
    profile: DocumentProfile
    initial_tier: ExtractionCostTier
    initial_strategy: str
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


def _looks_form_fillable(text: str) -> bool:
    lowered = text.lower()
    markers = ("/tx", "form field", "checkbox", "signature")
    return any(marker in lowered for marker in markers)


def _layout_from_signals(
    table_marker_count: int,
    line_count: int,
    short_line_ratio: float,
    cfg: ExtractionConfig,
) -> LayoutComplexity:
    if (
        table_marker_count >= cfg.min_table_markers_for_table_strategy
        and short_line_ratio > cfg.mixed_layout_short_line_ratio_min
    ):
        return LayoutComplexity.MIXED
    if table_marker_count >= cfg.min_table_markers_for_table_strategy:
        return LayoutComplexity.TABLE_HEAVY
    if short_line_ratio > cfg.multi_column_short_line_ratio_min and line_count > 10:
        return LayoutComplexity.MULTI_COLUMN
    return LayoutComplexity.SINGLE_COLUMN


def profile_document(
    document: DocumentInput,
    cfg: ExtractionConfig,
    domain_classifier: DomainHintClassifier,
) -> DocumentProfile:
    text = document.content or ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    line_count = len(lines)
    short_lines = sum(1 for line in lines if len(line) < 45)

    char_count = len(text)
    page_estimate = max(1, text.count("\f") + 1)
    char_density = char_count / page_estimate
    table_marker_count = _table_markers(text)
    printable_ratio = _printable_ratio(text)

    # Heuristic image ratio proxy for local/offline classification.
    if document.mime_type.startswith("image/"):
        image_ratio = 0.95
    elif document.mime_type == "application/pdf" and char_count < 200:
        image_ratio = 0.8
    elif document.mime_type == "application/pdf":
        image_ratio = 0.25
    else:
        image_ratio = 0.05

    font_metadata_present = printable_ratio > 0.85 and char_density >= cfg.native_char_density_min
    zero_text = char_count == 0
    mixed_mode_pages = (
        document.mime_type == "application/pdf"
        and cfg.mixed_image_ratio_min <= image_ratio < cfg.scanned_image_ratio_min
    )
    form_fillable = _looks_form_fillable(text)

    if zero_text:
        origin_type = OriginType.SCANNED_IMAGE
    elif image_ratio >= cfg.scanned_image_ratio_min and not font_metadata_present:
        origin_type = OriginType.SCANNED_IMAGE
    elif mixed_mode_pages:
        origin_type = OriginType.MIXED
    else:
        origin_type = OriginType.NATIVE_DIGITAL

    short_line_ratio = short_lines / max(1, line_count)
    layout_complexity = _layout_from_signals(table_marker_count, line_count, short_line_ratio, cfg)
    domain_hint = domain_classifier.classify(text, cfg.domain_keywords)

    if origin_type == OriginType.SCANNED_IMAGE or zero_text:
        extraction_cost = ExtractionCostTier.C_VISION_AUGMENTED
    elif (
        origin_type == OriginType.MIXED
        or layout_complexity in {LayoutComplexity.MULTI_COLUMN, LayoutComplexity.TABLE_HEAVY, LayoutComplexity.FIGURE_HEAVY}
        or (document.mime_type == "application/pdf" and cfg.prefer_layout_for_pdf and char_count >= cfg.min_chars_for_layout)
    ):
        extraction_cost = ExtractionCostTier.B_LAYOUT_AWARE
    else:
        extraction_cost = ExtractionCostTier.A_FAST_TEXT

    confidence = min(
        1.0,
        max(
            0.35,
            (printable_ratio * 0.45)
            + ((1.0 - image_ratio) * 0.25)
            + (0.20 if font_metadata_present else 0.0)
            + (0.10 if not zero_text else 0.0),
        ),
    )

    return DocumentProfile(
        origin_type=origin_type,
        layout_complexity=layout_complexity,
        language="am" if any("\u1200" <= c <= "\u137F" for c in text) else "en",
        domain_hint=domain_hint,
        extraction_cost=extraction_cost,
        confidence=confidence,
        char_count=char_count,
        char_density=char_density,
        image_ratio=image_ratio,
        font_metadata_present=font_metadata_present,
        table_marker_count=table_marker_count,
        zero_text=zero_text,
        mixed_mode_pages=mixed_mode_pages,
        form_fillable=form_fillable,
    )


def build_triage_decision(
    document: DocumentInput,
    cfg: ExtractionConfig,
    domain_classifier: DomainHintClassifier | None = None,
) -> TriageDecision:
    classifier = domain_classifier or KeywordDomainHintClassifier()
    profile = profile_document(document, cfg, classifier)
    initial_tier = profile.extraction_cost
    initial_strategy = cfg.strategy_by_cost.get(initial_tier.value, cfg.default_strategy)

    reason = (
        f"origin={profile.origin_type.value}; layout={profile.layout_complexity.value}; "
        f"domain={profile.domain_hint.value}; cost={profile.extraction_cost.value}"
    )

    return TriageDecision(
        profile=profile,
        initial_tier=initial_tier,
        initial_strategy=initial_strategy,
        reason=reason,
        confidence=profile.confidence,
    )
