from __future__ import annotations

from abc import ABC, abstractmethod

from rataz_tech.core.models import DomainHint


class DomainHintClassifier(ABC):
    @abstractmethod
    def classify(self, text: str, keyword_map: dict[str, list[str]]) -> DomainHint:
        raise NotImplementedError


class KeywordDomainHintClassifier(DomainHintClassifier):
    def classify(self, text: str, keyword_map: dict[str, list[str]]) -> DomainHint:
        lowered = text.lower()
        scores: dict[str, int] = {}
        for label, keywords in keyword_map.items():
            scores[label] = sum(lowered.count(keyword.lower()) for keyword in keywords)

        best_label = max(scores, key=scores.get) if scores else "general"
        if scores.get(best_label, 0) == 0:
            return DomainHint.GENERAL

        mapping = {
            "finance": DomainHint.FINANCE,
            "legal": DomainHint.LEGAL,
            "assessment": DomainHint.ASSESSMENT,
            "fiscal": DomainHint.FISCAL,
            "general": DomainHint.GENERAL,
        }
        return mapping.get(best_label, DomainHint.GENERAL)
