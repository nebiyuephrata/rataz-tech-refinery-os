from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from pydantic import BaseModel, Field

from rataz_tech.core.models import BBox, DocumentInput


class ParsedLayoutBlock(BaseModel):
    page: int = Field(ge=1)
    text: str
    bbox: BBox
    reading_order: int = Field(ge=1)


class ParsedTable(BaseModel):
    page: int = Field(ge=1)
    headers: List[str]
    rows: List[List[str]]
    bbox: BBox


class ParsedFigure(BaseModel):
    page: int = Field(ge=1)
    caption: str
    bbox: BBox


class LayoutAdapterResult(BaseModel):
    blocks: List[ParsedLayoutBlock] = Field(default_factory=list)
    tables: List[ParsedTable] = Field(default_factory=list)
    figures: List[ParsedFigure] = Field(default_factory=list)


class LayoutAdapter(ABC):
    provider_name: str

    @abstractmethod
    def available(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def parse(self, document: DocumentInput) -> LayoutAdapterResult:
        raise NotImplementedError


class DoclingLayoutAdapter(LayoutAdapter):
    provider_name = "docling"

    def available(self) -> bool:
        try:
            import docling  # noqa: F401

            return True
        except ImportError:
            return False

    def parse(self, document: DocumentInput) -> LayoutAdapterResult:
        # Real parser integration point; deterministic stub until connector is added.
        lines = [line.strip() for line in document.content.splitlines() if line.strip()]
        if not lines and document.content.strip():
            lines = [document.content.strip()]
        blocks = [
            ParsedLayoutBlock(page=1, text=line, bbox=BBox(x0=0, y0=i * 10.0, x1=100, y1=(i + 1) * 10.0), reading_order=i + 1)
            for i, line in enumerate(lines)
        ]
        return LayoutAdapterResult(blocks=blocks)


class MinerULayoutAdapter(LayoutAdapter):
    provider_name = "mineru"

    def available(self) -> bool:
        try:
            import mineru  # noqa: F401

            return True
        except ImportError:
            return False

    def parse(self, document: DocumentInput) -> LayoutAdapterResult:
        lines = [line.strip() for line in document.content.splitlines() if line.strip()]
        if not lines and document.content.strip():
            lines = [document.content.strip()]
        blocks = [
            ParsedLayoutBlock(page=1, text=line, bbox=BBox(x0=0, y0=i * 10.0, x1=100, y1=(i + 1) * 10.0), reading_order=i + 1)
            for i, line in enumerate(lines)
        ]
        return LayoutAdapterResult(blocks=blocks)


def build_layout_adapter(tool_name: str) -> LayoutAdapter:
    if tool_name == "docling_layout":
        return DoclingLayoutAdapter()
    if tool_name == "mineru_layout":
        return MinerULayoutAdapter()
    # Fallback: use docling-style deterministic parser contract
    return DoclingLayoutAdapter()
