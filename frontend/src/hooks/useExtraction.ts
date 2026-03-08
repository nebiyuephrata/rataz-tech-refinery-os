import { useMutation, useQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useState } from "react";

import { fetchAudit, fetchPageIndex, queryDocument, queryStructured, uploadDocument } from "../lib/api";
import type { PipelineResult, QueryResponse, StoredPageIndexResponse, StructuredQueryResponse } from "../lib/types";

export type StageState = { id: string; label: string; state: "idle" | "running" | "done" | "error" };

const BASE_STAGES: StageState[] = [
  { id: "ingest", label: "Ingestion", state: "idle" },
  { id: "extraction", label: "Extraction", state: "idle" },
  { id: "chunking", label: "Semantic Chunking", state: "idle" },
  { id: "indexing", label: "Indexing", state: "idle" }
];

export function useExtraction() {
  const [result, setResult] = useState<PipelineResult | null>(null);
  const [queryResult, setQueryResult] = useState<QueryResponse | null>(null);
  const [structuredResult, setStructuredResult] = useState<StructuredQueryResponse | null>(null);
  const [pageIndex, setPageIndex] = useState<StoredPageIndexResponse | null>(null);
  const [currentFileName, setCurrentFileName] = useState<string | null>(null);
  const [queryText, setQueryText] = useState("provenance");
  const [stages, setStages] = useState<StageState[]>(BASE_STAGES);

  const auditQuery = useQuery({
    queryKey: ["audit"],
    queryFn: () => fetchAudit(20),
    refetchInterval: 1500
  });

  const uploadMutation = useMutation({
    mutationFn: uploadDocument,
    onMutate: () => {
      setResult(null);
      setQueryResult(null);
      setStructuredResult(null);
      setPageIndex(null);
      setStages([
        { id: "ingest", label: "Ingestion", state: "running" },
        { id: "extraction", label: "Extraction", state: "idle" },
        { id: "chunking", label: "Semantic Chunking", state: "idle" },
        { id: "indexing", label: "Indexing", state: "idle" }
      ]);
    },
    onSuccess: (data) => {
      setResult(data);
      setStages([
        { id: "ingest", label: "Ingestion", state: "done" },
        { id: "extraction", label: "Extraction", state: "done" },
        { id: "chunking", label: "Semantic Chunking", state: "done" },
        { id: "indexing", label: "Indexing", state: "done" }
      ]);
    },
    onError: () => {
      setStages((prev) => prev.map((stage) => ({ ...stage, state: stage.state === "done" ? "done" : "error" })));
    }
  });

  const pageIndexQuery = useQuery({
    queryKey: ["pageindex", result?.extraction.document_id],
    queryFn: async () => {
      if (!result?.extraction.document_id) return null;
      return fetchPageIndex(result.extraction.document_id);
    },
    enabled: Boolean(result?.extraction.document_id)
  });

  useEffect(() => {
    if (pageIndexQuery.data !== undefined) {
      setPageIndex(pageIndexQuery.data);
    }
  }, [pageIndexQuery.data]);

  const queryMutation = useMutation({
    mutationFn: async (query: string) => {
      const financialIntent = /\b(profit|loss|revenue|income|expense|ebitda|ebit|net)\b/i.test(query);
      if (financialIntent && result?.extraction.document_id) {
        const structured = await queryStructured(result.extraction.document_id, query, 5);
        if (structured.rows.length > 0) {
          return { mode: "structured" as const, data: structured };
        }
        const semantic = await queryDocument(query, "en");
        return {
          mode: "semantic_fallback" as const,
          data: semantic,
          structured
        };
      }
      const data = await queryDocument(query, "en");
      return { mode: "semantic" as const, data };
    },
    onSuccess: (payload) => {
      if (payload.mode === "structured") {
        setStructuredResult(payload.data);
        setQueryResult(null);
      } else if (payload.mode === "semantic_fallback") {
        setStructuredResult(payload.structured);
        setQueryResult(payload.data);
      } else {
        setQueryResult(payload.data);
        setStructuredResult(null);
      }
    }
  });

  const onUpload = useCallback(
    (file: File) => {
      setCurrentFileName(file.name);
      uploadMutation.mutate(file);
    },
    [uploadMutation]
  );
  const onQuery = useCallback(() => queryMutation.mutate(queryText), [queryMutation, queryText]);

  const lastRoutes = useMemo(
    () => (auditQuery.data ?? []).slice(-5).map((record) => `${record.method} ${record.route}`),
    [auditQuery.data]
  );

  return {
    stages,
    result,
    queryResult,
    structuredResult,
    queryText,
    setQueryText,
    pageIndex,
    currentFileName,
    onUpload,
    onQuery,
    uploading: uploadMutation.isPending,
    querying: queryMutation.isPending,
    uploadError: uploadMutation.error instanceof Error ? uploadMutation.error.message : null,
    queryError: queryMutation.error instanceof Error ? queryMutation.error.message : null,
    lastRoutes
  };
}
