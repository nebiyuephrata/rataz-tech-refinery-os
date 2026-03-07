from __future__ import annotations

from collections import Counter
from typing import Iterable

from rataz_tech.core.models import (
    AuditEvent,
    ChunkingResult,
    PageIndexBuildResult,
    PageIndexHit,
    PageIndexNode,
    PageIndexQueryResponse,
    ProvenanceChain,
    StageName,
)
from rataz_tech.core.text import tokenize


_STOPWORDS = {
    "the",
    "and",
    "to",
    "of",
    "in",
    "for",
    "on",
    "with",
    "a",
    "an",
    "is",
    "are",
}


def _safe_page(chunk) -> int:
    if chunk.provenance and chunk.provenance[0].spatial:
        return max(1, int(chunk.provenance[0].spatial.page))
    return 1


def _keywords(text: str, top_n: int = 5) -> list[str]:
    counts = Counter(tok for tok in tokenize(text) if tok not in _STOPWORDS and len(tok) > 2)
    return [tok for tok, _ in counts.most_common(top_n)]


def _count_nodes(node: PageIndexNode) -> int:
    return 1 + sum(_count_nodes(c) for c in node.children)


class PageIndexBuilder:
    def __init__(self, group_size: int = 5) -> None:
        self.group_size = max(1, group_size)

    def build(self, chunked: ChunkingResult, trace_id: str = "") -> PageIndexBuildResult:
        chunks = chunked.chunks
        if not chunks:
            root = PageIndexNode(node_id=f"{chunked.document_id}:root", title="Document", page_start=1, page_end=1)
            return PageIndexBuildResult(document_id=chunked.document_id, trace_id=trace_id, root=root, node_count=1)

        children: list[PageIndexNode] = []
        for i in range(0, len(chunks), self.group_size):
            group = chunks[i : i + self.group_size]
            first = group[0]
            text_join = " ".join(c.text for c in group)
            start_page = min(_safe_page(c) for c in group)
            end_page = max(_safe_page(c) for c in group)
            title_words = (first.text or "section").split()[:6]
            title = " ".join(title_words) or f"Section {len(children) + 1}"
            summary = text_join[:220]

            children.append(
                PageIndexNode(
                    node_id=f"{chunked.document_id}:sec{len(children) + 1}",
                    title=title,
                    page_start=start_page,
                    page_end=end_page,
                    summary=summary,
                    keywords=_keywords(text_join),
                    chunk_ids=[c.chunk_id for c in group],
                    children=[],
                )
            )

        root = PageIndexNode(
            node_id=f"{chunked.document_id}:root",
            title="Document Root",
            page_start=min(c.page_start for c in children),
            page_end=max(c.page_end for c in children),
            summary=f"Auto-built page index with {len(children)} sections",
            keywords=list(dict.fromkeys(k for c in children for k in c.keywords))[:10],
            chunk_ids=[],
            children=children,
        )

        return PageIndexBuildResult(
            document_id=chunked.document_id,
            trace_id=trace_id,
            root=root,
            node_count=_count_nodes(root),
        )


class PageIndexRetriever:
    def _iter_nodes(self, node: PageIndexNode, path: list[str] | None = None) -> Iterable[tuple[PageIndexNode, list[str]]]:
        current_path = (path or []) + [node.title]
        yield node, current_path
        for child in node.children:
            yield from self._iter_nodes(child, current_path)

    def query(self, root: PageIndexNode, document_id: str, query: str, top_k: int, trace_id: str = "") -> PageIndexQueryResponse:
        query_tokens = set(tokenize(query))
        scored: list[PageIndexHit] = []

        for node, path in self._iter_nodes(root):
            if node.node_id.endswith(":root"):
                continue
            node_tokens = set(tokenize(f"{node.title} {node.summary} {' '.join(node.keywords)}"))
            overlap = len(query_tokens & node_tokens)
            denom = max(1, len(query_tokens))
            score = overlap / denom
            if score <= 0:
                continue

            scored.append(
                PageIndexHit(
                    node_id=node.node_id,
                    title=node.title,
                    score=score,
                    summary=node.summary,
                    page_start=node.page_start,
                    page_end=node.page_end,
                    reasoning_path=path,
                    provenance=[
                        ProvenanceChain(
                            document_name=document_id,
                            page_number=node.page_start,
                            content_hash=f"{node.node_id}-hash",
                        )
                    ],
                )
            )

        hits = sorted(scored, key=lambda h: h.score, reverse=True)[:top_k]
        return PageIndexQueryResponse(
            document_id=document_id,
            query=query,
            trace_id=trace_id,
            hits=hits,
            audit=[
                AuditEvent(
                    stage=StageName.QUERYING,
                    message="PageIndex tree query executed",
                    metadata={"top_k": str(top_k), "hits": str(len(hits))},
                )
            ],
        )
