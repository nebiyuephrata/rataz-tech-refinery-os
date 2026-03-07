from __future__ import annotations

from abc import ABC, abstractmethod
import hashlib

from rataz_tech.core.models import AuditEvent, BBox, Chunk, ChunkingResult, NormalizationResult, PageRef, StageName


class ChunkingStrategy(ABC):
    @abstractmethod
    def chunk(self, normalized: NormalizationResult) -> ChunkingResult:
        raise NotImplementedError


class SlidingWindowChunkingStrategy(ChunkingStrategy):
    def __init__(self, max_chars: int, overlap_chars: int) -> None:
        self._max = max_chars
        self._overlap = overlap_chars

    def chunk(self, normalized: NormalizationResult) -> ChunkingResult:
        chunks = []
        idx = 0
        for unit in normalized.units:
            text = unit.normalized_text
            start = 0
            while start < len(text):
                end = min(len(text), start + self._max)
                piece = text[start:end]
                chunks.append(
                    Chunk(
                        chunk_id=f"{normalized.document_id}:c{idx}",
                        document_id=normalized.document_id,
                        text=piece,
                        source_unit_ids=[unit.unit_id],
                        provenance=[unit.provenance],
                        page_refs=[
                            PageRef(
                                page_start=unit.provenance.spatial.page if unit.provenance.spatial else 1,
                                page_end=unit.provenance.spatial.page if unit.provenance.spatial else 1,
                            )
                        ],
                        bounding_box=(
                            BBox(
                                x0=unit.provenance.spatial.x0,
                                y0=unit.provenance.spatial.y0,
                                x1=unit.provenance.spatial.x1,
                                y1=unit.provenance.spatial.y1,
                            )
                            if unit.provenance.spatial
                            else None
                        ),
                        parent_section="root",
                        content_hash=hashlib.sha256(piece.encode("utf-8", errors="ignore")).hexdigest(),
                    )
                )
                idx += 1
                if end == len(text):
                    break
                start = max(0, end - self._overlap)

        return ChunkingResult(
            document_id=normalized.document_id,
            chunks=chunks,
            audit=[
                AuditEvent(
                    stage=StageName.CHUNKING,
                    message="Sliding window chunking completed",
                    metadata={"max_chars": str(self._max), "overlap_chars": str(self._overlap)},
                )
            ],
        )
