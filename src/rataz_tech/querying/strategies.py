from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Tuple

from rataz_tech.core.config import PipelineConfig
from rataz_tech.core.models import AuditEvent, Chunk, QueryHit, QueryRequest, QueryResponse, StageName
from rataz_tech.core.text import tokenize
from rataz_tech.indexing.strategies import InvertedIndexStore
from rataz_tech.querying.semantic import (
    BGESentenceTransformerEmbedder,
    FAISSVectorStore,
    HashingEmbedder,
    HybridRetriever,
    InMemoryVectorStore,
    SemanticQueryConfig,
)


class QueryStrategy(ABC):
    @abstractmethod
    def query(self, request: QueryRequest) -> QueryResponse:
        raise NotImplementedError


class HybridDeterministicQueryStrategy(QueryStrategy):
    def __init__(self, store: InvertedIndexStore, config: PipelineConfig) -> None:
        self.store = store
        self.config = config

    def query(self, request: QueryRequest) -> QueryResponse:
        toks = tokenize(request.query)
        scores = defaultdict(float)
        for tok in toks:
            for cid in self.store.postings.get(tok, []):
                scores[cid] += 1.0

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        max_results = min(request.max_results, self.config.max_query_results)
        hits = []
        for cid, sc in ranked[:max_results]:
            text = self.store.chunks[cid]
            hits.append(
                QueryHit(
                    chunk_id=cid,
                    score=sc / max(1, len(toks)),
                    snippet=text[:200],
                    provenance=self.store.provenance.get(cid, []),
                )
            )

        top_score = hits[0].score if hits else 0.0
        should_escalate = top_score < self.config.confidence_threshold
        llm_enabled = self.config.enable_llm_escalation

        escalated = bool(should_escalate and llm_enabled)
        reason = None
        if should_escalate and not llm_enabled:
            reason = "Low confidence; LLM escalation disabled by config"
        elif escalated:
            reason = "Low confidence; escalation path enabled"

        return QueryResponse(
            query=request.query,
            language=request.language,
            hits=hits,
            escalated=escalated,
            reason=reason,
            audit=[
                AuditEvent(
                    stage=StageName.QUERYING,
                    message="Hybrid deterministic query executed",
                    metadata={"token_count": str(len(toks)), "top_score": str(top_score)},
                )
            ],
        )


class SemanticHybridQueryStrategy(QueryStrategy):
    def __init__(self, store: InvertedIndexStore, config: PipelineConfig) -> None:
        self.store = store
        self.config = config
        self.semantic = config.semantic_query
        self._retriever: HybridRetriever | None = None
        self._indexed_ids: set[str] = set()
        self._embedder_provider = self.semantic.embedder_provider
        self._vector_provider = self.semantic.vector_store_provider
        self._fallback_reason = ""

    def _build_retriever(self) -> HybridRetriever:
        embedder, embedder_provider, embedder_fallback = self._build_embedder()
        vector_store, vector_provider, vector_fallback = self._build_vector_store(embedder)
        self._embedder_provider = embedder_provider
        self._vector_provider = vector_provider
        fallback_reasons = [reason for reason in [embedder_fallback, vector_fallback] if reason]
        self._fallback_reason = "; ".join(fallback_reasons)
        return HybridRetriever(
            config=SemanticQueryConfig(
                enabled=self.semantic.enabled,
                top_k=self.semantic.top_k,
                lexical_weight=self.semantic.lexical_weight,
                semantic_weight=self.semantic.semantic_weight,
            ),
            embedder=embedder,
            vector_store=vector_store,
        )

    def _build_embedder(self):
        requested = self.semantic.embedder_provider
        if requested == "bge-small":
            try:
                import sentence_transformers  # noqa: F401

                return (
                    BGESentenceTransformerEmbedder(model_name=self.semantic.bge_model_name),
                    "bge-small",
                    "",
                )
            except Exception as exc:
                return (
                    HashingEmbedder(dim=self.semantic.hashing_dim),
                    "hashing",
                    f"embedder fallback: {exc.__class__.__name__}",
                )
        return HashingEmbedder(dim=self.semantic.hashing_dim), "hashing", ""

    def _build_vector_store(self, embedder) -> Tuple[object, str, str]:
        requested = self.semantic.vector_store_provider
        if requested == "faiss":
            dim = embedder.dim if isinstance(embedder, HashingEmbedder) else self.semantic.hashing_dim
            try:
                return FAISSVectorStore(dim=dim), "faiss", ""
            except Exception as exc:
                return InMemoryVectorStore(), "inmemory", f"vector-store fallback: {exc.__class__.__name__}"
        return InMemoryVectorStore(), "inmemory", ""

    def _sync_store_chunks(self) -> None:
        if self._retriever is None:
            self._retriever = self._build_retriever()
        new_chunks: list[Chunk] = []
        for chunk_id, text in self.store.chunks.items():
            if chunk_id in self._indexed_ids:
                continue
            new_chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    document_id="unknown",
                    text=text,
                    source_unit_ids=[],
                    provenance=self.store.provenance.get(chunk_id, []),
                )
            )
        if new_chunks:
            self._retriever.add_chunks(new_chunks)
            self._indexed_ids.update(c.chunk_id for c in new_chunks)

    def query(self, request: QueryRequest) -> QueryResponse:
        self._sync_store_chunks()
        assert self._retriever is not None
        max_results = min(request.max_results, self.config.max_query_results)
        hits_raw = self._retriever.query(request.query, top_k=max_results)

        hits: list[QueryHit] = []
        for hit in hits_raw:
            text = self.store.chunks.get(hit.chunk_id, "")
            hits.append(
                QueryHit(
                    chunk_id=hit.chunk_id,
                    score=hit.score,
                    snippet=text[:200],
                    provenance=self.store.provenance.get(hit.chunk_id, []),
                )
            )

        top_score = hits[0].score if hits else 0.0
        should_escalate = top_score < self.config.confidence_threshold
        llm_enabled = self.config.enable_llm_escalation
        escalated = bool(should_escalate and llm_enabled)
        reason = None
        if should_escalate and not llm_enabled:
            reason = "Low confidence; LLM escalation disabled by config"
        elif escalated:
            reason = "Low confidence; escalation path enabled"

        metadata = {
            "semantic_enabled": str(self.semantic.enabled).lower(),
            "token_count": str(len(tokenize(request.query))),
            "top_score": str(top_score),
            "embedder_provider": self._embedder_provider,
            "vector_store_provider": self._vector_provider,
            "lexical_weight": str(self.semantic.lexical_weight),
            "semantic_weight": str(self.semantic.semantic_weight),
        }
        if self._fallback_reason:
            metadata["fallback_reason"] = self._fallback_reason

        return QueryResponse(
            query=request.query,
            language=request.language,
            hits=hits,
            escalated=escalated,
            reason=reason,
            audit=[
                AuditEvent(
                    stage=StageName.QUERYING,
                    message="Semantic hybrid query executed",
                    metadata=metadata,
                )
            ],
        )
