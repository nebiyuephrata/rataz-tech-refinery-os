import type { PipelineResult, QueryResponse, RequestAuditRecord, StoredPageIndexResponse, StructuredQueryResponse } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export async function uploadDocument(file: File): Promise<PipelineResult> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/ingest/file`, {
    method: "POST",
    body: formData
  });

  if (!response.ok) {
    const body = await safeError(response);
    throw new Error(body || "Failed to upload document");
  }

  return response.json() as Promise<PipelineResult>;
}

export async function queryDocument(query: string, language: "en" | "am" = "en"): Promise<QueryResponse> {
  const response = await fetch(`${API_BASE_URL}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, language, max_results: 5 })
  });

  if (!response.ok) {
    const body = await safeError(response);
    throw new Error(body || "Query failed");
  }

  return response.json() as Promise<QueryResponse>;
}

export async function queryStructured(documentId: string, query: string, limit = 5): Promise<StructuredQueryResponse> {
  const response = await fetch(`${API_BASE_URL}/query/structured`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ document_id: documentId, query, limit })
  });
  if (!response.ok) {
    const body = await safeError(response);
    throw new Error(body || "Structured query failed");
  }
  return response.json() as Promise<StructuredQueryResponse>;
}

export async function fetchAudit(limit = 20): Promise<RequestAuditRecord[]> {
  const response = await fetch(`${API_BASE_URL}/audit/requests?limit=${limit}`);
  if (!response.ok) {
    return [];
  }
  const body = (await response.json()) as { records: RequestAuditRecord[] };
  return body.records ?? [];
}

export async function fetchPageIndex(documentId: string): Promise<StoredPageIndexResponse | null> {
  const response = await fetch(`${API_BASE_URL}/pageindex/${encodeURIComponent(documentId)}`);
  if (!response.ok) {
    return null;
  }
  return response.json() as Promise<StoredPageIndexResponse>;
}

async function safeError(response: Response): Promise<string | null> {
  try {
    const body = (await response.json()) as { detail?: string; error?: string };
    return body.detail ?? body.error ?? null;
  } catch {
    return null;
  }
}
