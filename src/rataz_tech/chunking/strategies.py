from __future__ import annotations

from abc import ABC, abstractmethod

from rataz_tech.core.models import AuditEvent, Chunk, ChunkingResult, NormalizationResult, StageName


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
