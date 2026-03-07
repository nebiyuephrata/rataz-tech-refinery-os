from __future__ import annotations

import hashlib
import re
from typing import Iterable

from pydantic import BaseModel, Field

from rataz_tech.core.models import BBox, Chunk, ChunkType, ChunkingResult, ExtractedDocument, LogicalDocumentUnit, PageRef, ProvenanceRecord, SpatialProvenance
from rataz_tech.core.text import tokenize


_SECTION_RE = re.compile(r"^\s*section\s+([a-z0-9 _-]+)", re.IGNORECASE)
_NUMBERED_LIST_RE = re.compile(r"(?m)^\s*\d+[\.)]\s+")
_XREF_RE = re.compile(r"see\s+section\s+([a-z0-9 _-]+)", re.IGNORECASE)


class ChunkValidator(BaseModel):
    max_tokens: int = Field(gt=0)

    def validate(self, ldus: list[LogicalDocumentUnit]) -> list[LogicalDocumentUnit]:
        for ldu in ldus:
            if not ldu.content.strip():
                raise ValueError(f"LDU {ldu.ldu_id} has empty content")
            if ldu.token_count < 0:
                raise ValueError(f"LDU {ldu.ldu_id} has invalid token_count")
            if not ldu.page_refs:
                raise ValueError(f"LDU {ldu.ldu_id} missing page_refs")
            if len(ldu.content_hash) < 8:
                raise ValueError(f"LDU {ldu.ldu_id} has invalid content_hash")
            if ldu.chunk_type == ChunkType.FIGURE and "caption" not in ldu.metadata:
                raise ValueError(f"Figure LDU {ldu.ldu_id} missing caption metadata")
            if ldu.chunk_type == ChunkType.TABLE and "table_headers" not in ldu.metadata:
                raise ValueError(f"Table LDU {ldu.ldu_id} missing table_headers metadata")
        return ldus


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def _infer_parent_section(text: str, fallback: str | None) -> str:
    if fallback:
        return fallback
    first = text.strip().splitlines()[0] if text.strip() else ""
    m = _SECTION_RE.search(first)
    if m:
        return m.group(1).strip().title()
    if len(first.split()) <= 8 and first and first[:1].isupper():
        return first.strip(" :")
    return "root"


def _resolve_xrefs(text: str) -> list[str]:
    out: list[str] = []
    for m in _XREF_RE.finditer(text):
        target = m.group(1).strip().lower().replace(" ", "_")
        out.append(f"xref:{target}")
    return out


def _split_numbered_list_if_needed(text: str, max_tokens: int) -> list[str]:
    toks = tokenize(text)
    if len(toks) <= max_tokens:
        return [text]
    if not _NUMBERED_LIST_RE.search(text):
        return [text]
    # Controlled split only when oversized.
    lines = [ln for ln in text.splitlines() if ln.strip()]
    chunks: list[str] = []
    buf: list[str] = []
    for ln in lines:
        candidate = "\n".join(buf + [ln])
        if len(tokenize(candidate)) > max_tokens and buf:
            chunks.append("\n".join(buf))
            buf = [ln]
        else:
            buf.append(ln)
    if buf:
        chunks.append("\n".join(buf))
    return chunks


def build_ldus(extracted_document: ExtractedDocument, max_tokens: int) -> list[LogicalDocumentUnit]:
    ldus: list[LogicalDocumentUnit] = []

    for block in extracted_document.text_blocks:
        parent_section = _infer_parent_section(block.content, block.parent_section)
        pieces = _split_numbered_list_if_needed(block.content, max_tokens=max_tokens)
        for idx, piece in enumerate(pieces):
            relationships = list(dict.fromkeys(block.chunk_relationships + _resolve_xrefs(piece)))
            ldu = LogicalDocumentUnit(
                ldu_id=f"{block.ldu_id}:txt{idx}",
                content=piece,
                chunk_type=ChunkType.TEXT,
                token_count=len(tokenize(piece)),
                page_refs=block.page_refs,
                bounding_box=block.bounding_box,
                content_hash=_hash(piece),
                parent_section=parent_section,
                chunk_relationships=relationships,
                metadata={"source": "text_block"},
            )
            ldus.append(ldu)

    for table in extracted_document.tables:
        header = " | ".join(table.headers)
        rows = [" | ".join(r) for r in table.rows]
        content = "\n".join([header] + rows)
        ldus.append(
            LogicalDocumentUnit(
                ldu_id=f"{table.table_id}:table",
                content=content,
                chunk_type=ChunkType.TABLE,
                token_count=len(tokenize(content)),
                page_refs=[PageRef(page_start=table.page_number, page_end=table.page_number)],
                bounding_box=table.bounding_box,
                content_hash=_hash(content),
                parent_section="table",
                chunk_relationships=[],
                metadata={"table_headers": header},
            )
        )

    for figure in extracted_document.figures:
        content = f"Figure {figure.figure_id}"
        ldus.append(
            LogicalDocumentUnit(
                ldu_id=f"{figure.figure_id}:figure",
                content=content,
                chunk_type=ChunkType.FIGURE,
                token_count=len(tokenize(content)),
                page_refs=[PageRef(page_start=figure.page_number, page_end=figure.page_number)],
                bounding_box=figure.bounding_box,
                content_hash=_hash(content),
                parent_section="figure",
                chunk_relationships=[],
                metadata={"caption": figure.caption},
            )
        )

    return ChunkValidator(max_tokens=max_tokens).validate(ldus)


def ldus_to_chunks(document_id: str, source_uri: str, ldus: Iterable[LogicalDocumentUnit]) -> list[Chunk]:
    chunks: list[Chunk] = []
    for idx, ldu in enumerate(ldus):
        page = ldu.page_refs[0].page_start
        if ldu.bounding_box is None:
            bbox = BBox(x0=0.0, y0=0.0, x1=1.0, y1=1.0)
        else:
            bbox = ldu.bounding_box
        provenance = ProvenanceRecord(
            source_uri=source_uri,
            extractor="semantic_chunking",
            record_id=f"{document_id}:chunk:{idx}",
            confidence=1.0,
            spatial=SpatialProvenance(page=page, x0=bbox.x0, y0=bbox.y0, x1=bbox.x1, y1=bbox.y1),
        )
        chunks.append(
            Chunk(
                chunk_id=f"{document_id}:c{idx}",
                document_id=document_id,
                text=ldu.content,
                source_unit_ids=[ldu.ldu_id],
                provenance=[provenance],
                chunk_type=ldu.chunk_type,
                page_refs=ldu.page_refs,
                bounding_box=ldu.bounding_box,
                parent_section=ldu.parent_section,
                content_hash=ldu.content_hash,
                chunk_relationships=ldu.chunk_relationships,
                metadata=ldu.metadata,
            )
        )
    return chunks


def ldus_to_chunking_result(document_id: str, source_uri: str, ldus: list[LogicalDocumentUnit]) -> ChunkingResult:
    from rataz_tech.core.models import AuditEvent, StageName

    chunks = ldus_to_chunks(document_id=document_id, source_uri=source_uri, ldus=ldus)
    return ChunkingResult(
        document_id=document_id,
        chunks=chunks,
        audit=[
            AuditEvent(
                stage=StageName.CHUNKING,
                message="Semantic LDU chunking completed",
                metadata={"ldu_count": str(len(ldus)), "chunk_count": str(len(chunks))},
            )
        ],
    )
