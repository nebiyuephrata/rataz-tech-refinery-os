from __future__ import annotations

from abc import ABC, abstractmethod
from io import BytesIO
from typing import Callable, Dict, List

from pydantic import BaseModel, Field
from PIL import Image

from rataz_tech.core.models import BBox, DocumentInput
from rataz_tech.extraction.pdf_parsers import resolve_source_path


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
        import pytesseract

        source_path = resolve_source_path(document.source_uri)
        if source_path and document.mime_type == "application/pdf":
            try:
                import fitz

                blocks: list[OCRTextBlock] = []
                pdf = fitz.open(source_path)
                try:
                    for page_no, page in enumerate(pdf, start=1):
                        pix = page.get_pixmap(dpi=220)
                        img = Image.open(BytesIO(pix.tobytes("png")))
                        text = (pytesseract.image_to_string(img) or "").strip()
                        if text:
                            blocks.append(
                                OCRTextBlock(
                                    page=page_no,
                                    text=text,
                                    bbox=BBox(x0=0, y0=0, x1=float(page.rect.width), y1=float(page.rect.height)),
                                )
                            )
                finally:
                    pdf.close()
                if blocks:
                    return OCRAdapterResult(blocks=blocks)
            except Exception:
                pass

        if source_path and document.mime_type.startswith("image/"):
            try:
                img = Image.open(source_path)
                text = (pytesseract.image_to_string(img) or "").strip()
                if text:
                    return OCRAdapterResult(
                        blocks=[
                            OCRTextBlock(
                                page=1,
                                text=text,
                                bbox=BBox(x0=0, y0=0, x1=float(img.size[0]), y1=float(img.size[1])),
                            )
                        ]
                    )
            except Exception:
                pass

        # Fallback: keep deterministic behavior for text-based inputs.
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


_OCR_ADAPTER_REGISTRY: Dict[str, Callable[[], OCRAdapter]] = {
    "tesseract_ocr": TesseractOCRAdapter,
}
_TABLE_ADAPTER_REGISTRY: Dict[str, Callable[[], TableAdapter]] = {
    "camelot_table": CamelotTableAdapter,
}


def register_ocr_adapter(name: str, factory: Callable[[], OCRAdapter]) -> None:
    _OCR_ADAPTER_REGISTRY[name] = factory


def register_table_adapter(name: str, factory: Callable[[], TableAdapter]) -> None:
    _TABLE_ADAPTER_REGISTRY[name] = factory


def build_ocr_adapter(name: str) -> OCRAdapter:
    if name in _OCR_ADAPTER_REGISTRY:
        return _OCR_ADAPTER_REGISTRY[name]()
    return TesseractOCRAdapter()


def build_table_adapter(name: str) -> TableAdapter:
    if name in _TABLE_ADAPTER_REGISTRY:
        return _TABLE_ADAPTER_REGISTRY[name]()
    return CamelotTableAdapter()
