from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from pydantic import BaseModel, Field

from rataz_tech.core.models import BBox, DocumentInput


class OCRTextBlock(BaseModel):
    page: int = Field(ge=1)
    text: str
    bbox: BBox


class OCRAdapterResult(BaseModel):
    blocks: List[OCRTextBlock] = Field(default_factory=list)


class TableRow(BaseModel):
    values: List[str]


class TableAdapterResult(BaseModel):
    headers: List[str] = Field(default_factory=list)
    rows: List[TableRow] = Field(default_factory=list)
    bbox: BBox = Field(default_factory=lambda: BBox(x0=0, y0=0, x1=1, y1=1))
    page: int = Field(default=1, ge=1)


class OCRAdapter(ABC):
    provider_name: str

    @abstractmethod
    def available(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def parse(self, document: DocumentInput) -> OCRAdapterResult:
        raise NotImplementedError


class TableAdapter(ABC):
    provider_name: str

    @abstractmethod
    def available(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def parse(self, document: DocumentInput) -> TableAdapterResult:
        raise NotImplementedError


class TesseractOCRAdapter(OCRAdapter):
    provider_name = "tesseract"

    def available(self) -> bool:
        try:
            import pytesseract  # noqa: F401

            return True
        except ImportError:
            return False

    def parse(self, document: DocumentInput) -> OCRAdapterResult:
        # Real image/pdf OCR connector point.
        text = document.content.strip() or ""
        blocks = [OCRTextBlock(page=1, text=text, bbox=BBox(x0=0, y0=0, x1=100, y1=100))] if text else []
        return OCRAdapterResult(blocks=blocks)


class CamelotTableAdapter(TableAdapter):
    provider_name = "camelot"

    def available(self) -> bool:
        try:
            import camelot  # noqa: F401

            return True
        except ImportError:
            return False

    def parse(self, document: DocumentInput) -> TableAdapterResult:
        # Real PDF table extraction connector point.
        lines = [line for line in document.content.splitlines() if line.strip()]
        if lines and "," in lines[0]:
            headers = [h.strip() for h in lines[0].split(",")]
            rows = [TableRow(values=[v.strip() for v in ln.split(",")]) for ln in lines[1:] if "," in ln]
            return TableAdapterResult(headers=headers, rows=rows, bbox=BBox(x0=0, y0=0, x1=100, y1=40), page=1)
        return TableAdapterResult(headers=[], rows=[], bbox=BBox(x0=0, y0=0, x1=1, y1=1), page=1)
