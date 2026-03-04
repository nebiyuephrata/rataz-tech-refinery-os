from __future__ import annotations

from rataz_tech.chunking.strategies import ChunkingStrategy, SlidingWindowChunkingStrategy
from rataz_tech.core.config import PipelineConfig


def build_chunker(name: str, pipeline: PipelineConfig) -> ChunkingStrategy:
    if name == "sliding_window":
        return SlidingWindowChunkingStrategy(
            max_chars=pipeline.max_chunk_chars,
            overlap_chars=pipeline.chunk_overlap_chars,
        )
    raise ValueError(f"Unknown chunker strategy: {name}")
