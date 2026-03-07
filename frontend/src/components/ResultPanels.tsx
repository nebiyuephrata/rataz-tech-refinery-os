import { memo, useMemo } from "react";

import type { PipelineResult, QueryResponse } from "../lib/types";

type Props = {
  result: PipelineResult | null;
  queryResult: QueryResponse | null;
  routes: string[];
};

function ResultPanels({ result, queryResult, routes }: Props) {
  const metrics = useMemo(() => {
    if (!result) return null;
    return {
      chunks: result.chunking.chunks.length,
      indexed: result.indexing.indexed.length,
      confidence: (result.extraction.strategy_confidence * 100).toFixed(1)
    };
  }, [result]);

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

      <section className="neon-border rounded-2xl bg-[var(--panel)] p-5 lg:col-span-2">
        <h3 className="font-display text-lg">Query Results</h3>
        {!queryResult ? (
          <p className="mt-3 text-sm text-[var(--text-soft)]">Run a query after ingestion.</p>
        ) : (
          <div className="mt-3 space-y-3">
            {queryResult.hits.map((hit) => (
              <article key={hit.chunk_id} className="rounded-lg border border-white/10 p-3">
                <p className="text-sm">{hit.snippet}</p>
                <p className="mt-2 text-xs text-cyan-300">score {hit.score.toFixed(3)}</p>
              </article>
            ))}
            {!queryResult.hits.length && <p className="text-sm text-rose-300">{queryResult.reason ?? "No hits"}</p>}
          </div>
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
