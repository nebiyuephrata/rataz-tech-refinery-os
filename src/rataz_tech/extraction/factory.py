from __future__ import annotations

from rataz_tech.extraction.strategies import (
    ExtractionStrategy,
    OCREmulationAdapter,
    PlainTextExtractionStrategy,
)


def build_extractor(name: str) -> ExtractionStrategy:
    if name == "plain_text":
        return PlainTextExtractionStrategy()
    if name == "ocr_adapter":
        return OCREmulationAdapter(PlainTextExtractionStrategy())
    raise ValueError(f"Unknown extractor strategy: {name}")
