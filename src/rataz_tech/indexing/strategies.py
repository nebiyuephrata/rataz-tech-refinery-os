from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Dict, Set

from rataz_tech.core.models import AuditEvent, ChunkingResult, IndexResult, IndexedChunk, StageName
from rataz_tech.core.text import tokenize


class IndexingStrategy(ABC):
    @abstractmethod
    def index(self, chunked: ChunkingResult) -> IndexResult:
        raise NotImplementedError


class InvertedIndexStore:
    def __init__(self) -> None:
        self.chunks: Dict[str, str] = {}
        self.provenance: Dict[str, list] = {}
        self.metadata: Dict[str, dict] = {}
        self.postings: Dict[str, Set[str]] = defaultdict(set)


class InvertedIndexingStrategy(IndexingStrategy):
    def __init__(self, store: InvertedIndexStore) -> None:
        self.store = store

    def index(self, chunked: ChunkingResult) -> IndexResult:
        indexed = []
        for chunk in chunked.chunks:
            self.store.chunks[chunk.chunk_id] = chunk.text
            self.store.provenance[chunk.chunk_id] = chunk.provenance
            self.store.metadata[chunk.chunk_id] = {
                "chunk_type": chunk.chunk_type.value,
                "page_refs": [p.model_dump() for p in chunk.page_refs],
                "content_hash": chunk.content_hash,
                "parent_section": chunk.parent_section or "",
            }
            tokens = tokenize(chunk.text)
            for tok in set(tokens):
                self.store.postings[tok].add(chunk.chunk_id)
            indexed.append(IndexedChunk(chunk_id=chunk.chunk_id, text=chunk.text, token_count=len(tokens)))

        return IndexResult(
            document_id=chunked.document_id,
            indexed=indexed,
            audit=[AuditEvent(stage=StageName.INDEXING, message="Inverted index updated")],
        )
