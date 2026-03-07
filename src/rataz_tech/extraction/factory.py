from __future__ import annotations

from rataz_tech.core.config import Settings
from rataz_tech.core.models import AuditEvent, DocumentInput, ExtractionCostTier, ExtractionResult, StageName
from rataz_tech.extraction.strategies import (
    ExtractionStrategy,
    FastTextExtractionStrategy,
    LayoutAwareExtractionStrategy,
    VisionAugmentedExtractionStrategy,
)
from rataz_tech.extraction.provenance_quality import evaluate_provenance_quality
from rataz_tech.extraction.triage import build_triage_decision


def _strategy_by_name(name: str, settings: Settings) -> ExtractionStrategy:
    if name == "plain_text":
        return FastTextExtractionStrategy()
    if name in {"docling_layout", "mineru_layout", "camelot_table", "pdfplumber_text", "pymupdf_text"}:
        return LayoutAwareExtractionStrategy(name)
    if name in {"vision_augmented", "tesseract_ocr"}:
        return VisionAugmentedExtractionStrategy(
            settings.extraction.vision_budget,
            tool_name=name,
            ocr_provider_name=settings.extraction.adapters.ocr,
            table_provider_name=settings.extraction.adapters.table,
        )
    raise ValueError(f"Unknown extractor strategy: {name}")


class AutoTriageExtractionStrategy(ExtractionStrategy):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def strategy_name(self) -> str:
        return "auto_triage"

    @property
    def tier_name(self) -> str:
        return "router"

    def _threshold_for_tier(self, tier: ExtractionCostTier) -> float:
        return self._settings.extraction.strategy_confidence_thresholds.get(tier.value, 0.75)

    def _next_tier(self, tier: ExtractionCostTier) -> ExtractionCostTier | None:
        order = self._settings.extraction.escalation.strategy_order
        try:
            idx = order.index(tier.value)
        except ValueError:
            return None
        if idx + 1 >= len(order):
            return None
        return ExtractionCostTier(order[idx + 1])

    def _strategy_for_tier(self, tier: ExtractionCostTier) -> ExtractionStrategy:
        name = self._settings.extraction.strategy_by_cost.get(tier.value, self._settings.extraction.default_strategy)
        return _strategy_by_name(name, self._settings)

    def extract(self, document: DocumentInput, *_: object) -> ExtractionResult:
        decision = build_triage_decision(document, self._settings.extraction)
        tier = decision.initial_tier

        escalation_path: list[str] = []
        final_result: ExtractionResult | None = None
        while tier is not None:
            strategy = self._strategy_for_tier(tier)
            escalation_path.append(tier.value)
            result = strategy.extract(document, decision.profile)

            threshold = self._threshold_for_tier(tier)
            if result.strategy_confidence >= threshold:
                final_result = result
                break

            next_tier = self._next_tier(tier)
            if next_tier is None:
                result.review_required = self._settings.extraction.escalation.review_on_final_low_confidence
                final_result = result
                break
            tier = next_tier

        assert final_result is not None
        final_result.profile = decision.profile
        final_result.escalation_path = escalation_path
        quality = evaluate_provenance_quality(final_result, self._settings.extraction.provenance_quality)
        if quality.review_required:
            final_result.review_required = True

        final_result.audit.append(
            AuditEvent(
                stage=StageName.EXTRACTION,
                message="Extraction triage decision",
                metadata={
                    "initial_tier": decision.initial_tier.value,
                    "initial_strategy": decision.initial_strategy,
                    "triage_reason": decision.reason,
                    "triage_confidence": f"{decision.confidence:.2f}",
                    "strategy_selected": final_result.strategy_used,
                    "strategy_confidence": f"{final_result.strategy_confidence:.2f}",
                    "escalation_path": ",".join(escalation_path),
                    "review_required": str(final_result.review_required).lower(),
                },
            )
        )
        final_result.audit.append(
            AuditEvent(
                stage=StageName.EXTRACTION,
                message="Provenance quality gate evaluated",
                metadata={
                    "quality_score": str(quality.score),
                    "unit_spatial_ratio": str(quality.unit_spatial_ratio),
                    "chain_bbox_ratio": str(quality.chain_bbox_ratio),
                    "content_hash_match_ratio": str(quality.content_hash_match_ratio),
                    "review_required": str(quality.review_required).lower(),
                },
            )
        )
        return final_result


def build_extractor(name: str, settings: Settings) -> ExtractionStrategy:
    if name == "auto_triage":
        return AutoTriageExtractionStrategy(settings)
    return _strategy_by_name(name, settings)
