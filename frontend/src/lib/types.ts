export type AuditEvent = {
  stage: string;
  message: string;
  trace_id: string;
  metadata: Record<string, string>;
};

export type ProvenanceRecord = {
  source_uri: string;
  extractor: string;
  record_id: string;
  confidence: number;
  spatial?: { page: number; x0: number; y0: number; x1: number; y1: number };
};

export type QueryHit = {
  chunk_id: string;
  score: number;
  snippet: string;
  provenance: ProvenanceRecord[];
};

export type PipelineResult = {
  trace_id: string;
  extraction: {
    document_id: string;
    strategy_used: string;
    strategy_confidence: number;
    review_required: boolean;
    audit: AuditEvent[];
  };
  chunking: { chunks: Array<{ chunk_id: string; text: string }>; audit: AuditEvent[] };
  indexing: { indexed: Array<{ chunk_id: string; token_count: number }>; audit: AuditEvent[] };
};

export type QueryResponse = {
  trace_id: string;
  hits: QueryHit[];
  reason?: string;
  audit: AuditEvent[];
};

export type RequestAuditRecord = {
  route: string;
  method: string;
  trace_id: string;
  document_id?: string;
  timestamp_utc: string;
};
