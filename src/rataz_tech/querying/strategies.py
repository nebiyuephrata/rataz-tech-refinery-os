from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict

from rataz_tech.core.config import PipelineConfig
from rataz_tech.core.models import AuditEvent, QueryHit, QueryRequest, QueryResponse, StageName
from rataz_tech.core.text import tokenize
from rataz_tech.indexing.strategies import InvertedIndexStore


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
