from __future__ import annotations

from rataz_tech.normalization.strategies import NormalizationStrategy, RuleBasedNormalizationStrategy


def build_normalizer(name: str) -> NormalizationStrategy:
    if name == "rule_based":
        return RuleBasedNormalizationStrategy()
    raise ValueError(f"Unknown normalizer strategy: {name}")
