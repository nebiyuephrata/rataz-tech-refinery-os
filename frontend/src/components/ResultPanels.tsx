import { memo, useMemo } from "react";

import type { PageIndexNode, PipelineResult, QueryResponse, StoredPageIndexResponse, StructuredQueryResponse } from "../lib/types";

type Props = {
  result: PipelineResult | null;
  queryResult: QueryResponse | null;
  structuredResult: StructuredQueryResponse | null;
  pageIndex: StoredPageIndexResponse | null;
  routes: string[];
};

function renderNode(node: PageIndexNode, depth = 0): JSX.Element {
  return (
    <div key={node.node_id} className="space-y-2">
      <div className="rounded-lg border border-white/10 bg-black/20 p-3" style={{ marginLeft: `${depth * 14}px` }}>
        <p className="text-sm font-semibold">{node.title}</p>
        <p className="text-xs text-[var(--text-soft)]">
          pages {node.page_start}-{node.page_end}
        </p>
        {node.summary && <p className="mt-1 text-xs text-[var(--text-soft)]">{node.summary}</p>}
        {!!node.key_entities?.length && (
          <p className="mt-1 text-[11px] text-cyan-200">entities: {node.key_entities.join(", ")}</p>
        )}
      </div>
      {!!node.children?.length && node.children.map((child) => renderNode(child, depth + 1))}
    </div>
  );
}

function ResultPanels({ result, queryResult, structuredResult, pageIndex, routes }: Props) {
  const metrics = useMemo(() => {
    if (!result) return null;
    return {
      chunks: result.chunking.chunks.length,
      indexed: result.indexing.indexed.length,
      confidence: (result.extraction.strategy_confidence * 100).toFixed(1)
    };
  }, [result]);
  const cost = useMemo(() => {
    const parseCost = (value?: string) => {
      const n = Number.parseFloat(value ?? "0");
      return Number.isFinite(n) ? n : 0;
    };
    const sumAudit = (audits: Array<{ metadata: Record<string, string> }>) =>
      audits.reduce((acc, event) => acc + parseCost(event.metadata?.estimated_cost_usd), 0);

    const extractionCost = result
      ? sumAudit(result.extraction.audit) + sumAudit(result.chunking.audit) + sumAudit(result.indexing.audit)
      : 0;
    const queryCost = (queryResult ? sumAudit(queryResult.audit) : 0) + (structuredResult ? sumAudit(structuredResult.audit) : 0);
    return {
      extraction: extractionCost,
      query: queryCost,
      total: extractionCost + queryCost
    };
  }, [queryResult, structuredResult, result]);
  const tableJson = useMemo(() => {
    const firstTable = result?.extraction.extracted_document?.tables?.[0];
    if (!firstTable) return null;
    return JSON.stringify(firstTable, null, 2);
  }, [result]);
  const hasStructuredRows = (structuredResult?.rows.length ?? 0) > 0;

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <section className="neon-border rounded-2xl bg-[var(--panel)] p-5">
        <h3 className="font-display text-lg">Extraction Summary</h3>
        {metrics ? (
          <ul className="mt-3 space-y-2 text-sm text-[var(--text-soft)]">
            <li>Strategy: {result?.extraction.strategy_used}</li>
            <li>Confidence: {metrics.confidence}%</li>
            <li>Chunks: {metrics.chunks}</li>
            <li>Indexed: {metrics.indexed}</li>
            <li>Review Required: {String(result?.extraction.review_required)}</li>
          </ul>
        ) : (
          <p className="mt-3 text-sm text-[var(--text-soft)]">Upload a file to view extraction metrics.</p>
        )}
      </section>

      <section className="neon-border rounded-2xl bg-[var(--panel)] p-5">
        <h3 className="font-display text-lg">Cost Ledger</h3>
        <ul className="mt-3 space-y-2 text-sm text-[var(--text-soft)]">
          <li>Extraction Cost: ${cost.extraction.toFixed(6)}</li>
          <li>Query Cost: ${cost.query.toFixed(6)}</li>
          <li className="text-cyan-200">Total Cost: ${cost.total.toFixed(6)}</li>
        </ul>
      </section>

      <section className="neon-border rounded-2xl bg-[var(--panel)] p-5 lg:col-span-1">
        <h3 className="font-display text-lg">Query Results</h3>
        {!queryResult && !structuredResult ? (
          <p className="mt-3 text-sm text-[var(--text-soft)]">Run a query after ingestion.</p>
        ) : hasStructuredRows && structuredResult ? (
          <div className="mt-3 space-y-3">
            {structuredResult.rows.map((row, idx) => (
              <article key={`${row.metric}-${idx}`} className="rounded-lg border border-white/10 p-3">
                <p className="text-sm font-semibold">{row.metric}</p>
                <p className="mt-1 text-sm text-cyan-100">
                  {row.value.toLocaleString()} {row.unit}
                </p>
                <p className="mt-1 text-xs text-[var(--text-soft)]">page {row.page_number}</p>
              </article>
            ))}
          </div>
        ) : queryResult ? (
          <div className="mt-3 space-y-3">
            {!!structuredResult && !hasStructuredRows && (
              <p className="text-sm text-amber-300">
                No exact structured fact found. Showing most relevant evidence from semantic search.
              </p>
            )}
            {queryResult.hits.map((hit) => (
              <article key={hit.chunk_id} className="rounded-lg border border-white/10 p-3">
                <p className="text-sm">{hit.snippet}</p>
                <p className="mt-2 text-xs text-cyan-300">score {hit.score.toFixed(3)}</p>
              </article>
            ))}
            {!queryResult.hits.length && <p className="text-sm text-rose-300">{queryResult.reason ?? "No hits"}</p>}
          </div>
        ) : (
          <p className="mt-3 text-sm text-[var(--text-soft)]">Run a query after ingestion.</p>
        )}
      </section>

      <section className="neon-border rounded-2xl bg-[var(--panel)] p-5 lg:col-span-3">
        <h3 className="font-display text-lg">Extracted Table JSON</h3>
        {tableJson ? (
          <pre className="mt-3 overflow-x-auto rounded-lg border border-white/10 bg-black/30 p-3 text-xs text-cyan-100">
            {tableJson}
          </pre>
        ) : (
          <p className="mt-3 text-sm text-[var(--text-soft)]">No extracted tables found in this document.</p>
        )}
      </section>

      <section className="neon-border rounded-2xl bg-[var(--panel)] p-5 lg:col-span-3">
        <h3 className="font-display text-lg">PageIndex Tree</h3>
        {pageIndex?.pageindex?.root ? (
          <div className="mt-3 space-y-2">{renderNode(pageIndex.pageindex.root)}</div>
        ) : (
          <p className="mt-3 text-sm text-[var(--text-soft)]">No page index available yet.</p>
        )}
      </section>

      <section className="neon-border rounded-2xl bg-[var(--panel)] p-5 lg:col-span-3">
        <h3 className="font-display text-lg">Live Request Feed</h3>
        <div className="mt-3 flex flex-wrap gap-2">
          {routes.length ? (
            routes.map((route, index) => (
              <span key={`${route}-${index}`} className="rounded-full border border-cyan-400/40 px-3 py-1 text-xs text-cyan-200">
                {route}
              </span>
            ))
          ) : (
            <p className="text-sm text-[var(--text-soft)]">No recent requests yet.</p>
          )}
        </div>
      </section>
    </div>
  );
}

export default memo(ResultPanels);
