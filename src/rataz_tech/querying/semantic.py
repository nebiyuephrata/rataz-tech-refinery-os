from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import hashlib
import math
from typing import List

from pydantic import BaseModel, Field

from rataz_tech.core.models import Chunk
from rataz_tech.core.text import tokenize


class SemanticQueryConfig(BaseModel):
    enabled: bool = True
    top_k: int = Field(default=5, ge=1)
    lexical_weight: float = Field(default=0.6, ge=0.0)
    semantic_weight: float = Field(default=0.4, ge=0.0)


class Embedder(ABC):
    provider_name: str

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        raise NotImplementedError


class HashingEmbedder(Embedder):
    provider_name = "hashing"

    def __init__(self, dim: int = 128) -> None:
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        toks = tokenize(text)
        if not toks:
            return vec
        for tok in toks:
            token_digest = hashlib.sha1(tok.encode("utf-8", errors="ignore")).hexdigest()
            idx = int(token_digest[:8], 16) % self.dim
            vec[idx] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


class BGESentenceTransformerEmbedder(Embedder):
    provider_name = "bge-small"

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5") -> None:
        self.model_name = model_name
        self._model = None

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed(self, text: str) -> list[float]:
        model = self._load()
        vec = model.encode([text], normalize_embeddings=True)[0]
        return [float(v) for v in vec]


class VectorStore(ABC):
    provider_name: str

    @abstractmethod
    def add(self, chunk_id: str, vector: list[float]) -> None:
        raise NotImplementedError

    @abstractmethod
    def search(self, query_vector: list[float], top_k: int) -> list[tuple[str, float]]:
        raise NotImplementedError


class InMemoryVectorStore(VectorStore):
    provider_name = "inmemory"

    def __init__(self) -> None:
        self._vectors: dict[str, list[float]] = {}

    def add(self, chunk_id: str, vector: list[float]) -> None:
        self._vectors[chunk_id] = vector

    def search(self, query_vector: list[float], top_k: int) -> list[tuple[str, float]]:
        scored: list[tuple[str, float]] = []
        for cid, vec in self._vectors.items():
            score = sum(a * b for a, b in zip(query_vector, vec))
            scored.append((cid, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]


class FAISSVectorStore(VectorStore):
    provider_name = "faiss"

    def __init__(self, dim: int) -> None:
        import faiss

        self._faiss = faiss
        self._index = faiss.IndexFlatIP(dim)
        self._ids: list[str] = []

    def add(self, chunk_id: str, vector: list[float]) -> None:
        import numpy as np

        self._ids.append(chunk_id)
        arr = np.array([vector], dtype="float32")
        self._index.add(arr)

    def search(self, query_vector: list[float], top_k: int) -> list[tuple[str, float]]:
        import numpy as np

        q = np.array([query_vector], dtype="float32")
        scores, idxs = self._index.search(q, top_k)
        out: list[tuple[str, float]] = []
        for score, idx in zip(scores[0], idxs[0]):
            if idx < 0 or idx >= len(self._ids):
                continue
            out.append((self._ids[idx], float(score)))
        return out


@dataclass
class HybridHit:
    chunk_id: str
    score: float


class HybridRetriever:
    def __init__(
        self,
        config: SemanticQueryConfig,
        embedder: Embedder | None = None,
        vector_store: VectorStore | None = None,
    ) -> None:
        self.config = config
        self.embedder = embedder or HashingEmbedder()
        self.vector_store = vector_store or InMemoryVectorStore()
        self._chunks: dict[str, Chunk] = {}
        self._chunk_hashes: dict[str, str] = {}

    def add_chunks(self, chunks: List[Chunk]) -> None:
        for c in chunks:
            content_hash = hashlib.sha256(c.text.encode("utf-8", errors="ignore")).hexdigest()
            if c.chunk_id in self._chunk_hashes and self._chunk_hashes[c.chunk_id] == content_hash:
                continue
            self._chunks[c.chunk_id] = c
            vec = self.embedder.embed(c.text)
            self.vector_store.add(c.chunk_id, vec)
            self._chunk_hashes[c.chunk_id] = content_hash

    def _lexical_scores(self, query: str) -> dict[str, float]:
        query_tokens = set(tokenize(query))
        scores: dict[str, float] = {}
        for cid, chunk in self._chunks.items():
            chunk_tokens = set(tokenize(chunk.text))
            overlap = len(query_tokens & chunk_tokens)
            scores[cid] = overlap / max(1, len(query_tokens))
        return scores

    def query(self, query: str, top_k: int | None = None) -> list[HybridHit]:
        k = top_k or self.config.top_k
        lexical = self._lexical_scores(query)
        if not self.config.enabled:
            items = sorted(lexical.items(), key=lambda x: x[1], reverse=True)[:k]
            return [HybridHit(chunk_id=cid, score=sc) for cid, sc in items if sc > 0]

        qvec = self.embedder.embed(query)
        semantic = dict(self.vector_store.search(qvec, k * 2))

        all_ids = set(lexical.keys()) | set(semantic.keys())
        fused: list[HybridHit] = []
        for cid in all_ids:
            sc = (self.config.lexical_weight * lexical.get(cid, 0.0)) + (
                self.config.semantic_weight * semantic.get(cid, 0.0)
            )
            if sc > 0:
                fused.append(HybridHit(chunk_id=cid, score=sc))

        fused.sort(key=lambda x: x.score, reverse=True)
        return fused[:k]
