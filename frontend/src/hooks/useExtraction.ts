import { useMutation, useQuery } from "@tanstack/react-query";
import { useCallback, useMemo, useState } from "react";

import { fetchAudit, queryDocument, uploadDocument } from "../lib/api";
import type { PipelineResult, QueryResponse } from "../lib/types";

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

  const queryMutation = useMutation({
    mutationFn: (query: string) => queryDocument(query, "en"),
    onSuccess: (data) => setQueryResult(data)
  });

  const onUpload = useCallback((file: File) => uploadMutation.mutate(file), [uploadMutation]);
  const onQuery = useCallback(() => queryMutation.mutate(queryText), [queryMutation, queryText]);

  const lastRoutes = useMemo(
    () => (auditQuery.data ?? []).slice(-5).map((record) => `${record.method} ${record.route}`),
    [auditQuery.data]
  );

  return {
    stages,
    result,
    queryResult,
    queryText,
    setQueryText,
    onUpload,
    onQuery,
    uploading: uploadMutation.isPending,
    querying: queryMutation.isPending,
    uploadError: uploadMutation.error instanceof Error ? uploadMutation.error.message : null,
    queryError: queryMutation.error instanceof Error ? queryMutation.error.message : null,
    lastRoutes
  };
}
