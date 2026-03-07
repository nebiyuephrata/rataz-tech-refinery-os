from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ParsedBlock:
    page: int
    text: str
    x0: float
    y0: float
    x1: float
    y1: float


def _parse_with_pdfplumber(path: Path) -> list[ParsedBlock]:
    import pdfplumber

    blocks: list[ParsedBlock] = []
    with pdfplumber.open(str(path)) as pdf:
        for page_idx, page in enumerate(pdf.pages, start=1):
            words = page.extract_words() or []
            for i, w in enumerate(words):
                text = (w.get("text") or "").strip()
                if not text:
                    continue
                blocks.append(
                    ParsedBlock(
                        page=page_idx,
                        text=text,
                        x0=float(w.get("x0", 0.0)),
                        y0=float(w.get("top", 0.0)),
                        x1=float(w.get("x1", 1.0)),
                        y1=float(w.get("bottom", 1.0)),
                    )
                )
            if not words:
                page_text = (page.extract_text() or "").strip()
                if page_text:
                    blocks.append(ParsedBlock(page=page_idx, text=page_text, x0=0.0, y0=0.0, x1=1.0, y1=1.0))
    return blocks


def _parse_with_pymupdf(path: Path) -> list[ParsedBlock]:
    import fitz

    blocks: list[ParsedBlock] = []
    doc = fitz.open(str(path))
    try:
        for page_idx, page in enumerate(doc, start=1):
            for b in page.get_text("blocks"):
                x0, y0, x1, y1, text, *_ = b
                text = (text or "").strip()
                if not text:
                    continue
                blocks.append(
                    ParsedBlock(
                        page=page_idx,
                        text=text,
                        x0=float(x0),
                        y0=float(y0),
                        x1=float(x1),
                        y1=float(y1),
                    )
                )
    finally:
        doc.close()
    return blocks


def parse_pdf_blocks(path: str) -> tuple[list[ParsedBlock], str]:
    source = Path(path)
    if not source.exists():
        return [], "source_not_found"

    try:
        blocks = _parse_with_pdfplumber(source)
        if blocks:
            return blocks, "pdfplumber"
    except Exception:
        pass

    try:
        blocks = _parse_with_pymupdf(source)
        if blocks:
            return blocks, "pymupdf"
    except Exception:
        pass

    return [], "fallback"


def resolve_source_path(source_uri: str) -> Optional[str]:
    if source_uri.startswith("file://"):
        return source_uri.replace("file://", "", 1)
    if source_uri.startswith("local://"):
        # local://path/to/file.pdf
        tail = source_uri.replace("local://", "", 1)
        if tail.startswith("/"):
            return tail
    return None
