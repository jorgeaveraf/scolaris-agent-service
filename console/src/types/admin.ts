export type DocumentStatus = "ready" | "processing" | "error" | string;

export interface DocumentSummary {
  id: string;
  filename: string;
  status: DocumentStatus;
  size_bytes: number;
  area: string | null;
  role: string | null;
  vigencia: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentDetail extends DocumentSummary {
  content_type: string | null;
  checksum: string;
  doc_id: string | null;
  chunks_count: number | null;
  last_ingested_at: string | null;
  error_msg: string | null;
}

export interface DocumentsListResponse {
  total: number;
  items: DocumentSummary[];
}

export interface ChunkItem {
  chunk_id: number;
  chunk_no: number;
  text_preview: string;
  tokens: number;
  metadata: Record<string, unknown> | null;
}

export interface ChunksListResponse {
  total: number;
  items: ChunkItem[];
}

export interface RehydrateResponse {
  id: string;
  status: string;
}

export interface LatencyStats {
  count: number;
  avg_ms: number | null;
  p50_ms: number | null;
  p95_ms: number | null;
  max_ms: number | null;
}

export interface HttpMetrics {
  endpoints: Record<string, LatencyStats>;
  errors: Record<string, number>;
}

export interface GraphMetrics {
  steps: Record<string, LatencyStats>;
}

export interface TokenBreakdown {
  requests: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  avg_total_tokens: number | null;
}

export interface TokenMetrics {
  by_endpoint: Record<string, TokenBreakdown>;
  totals: TokenBreakdown | null;
}

export interface IngestionDocuments {
  total: number;
  ready: number;
  processing: number;
  error: number;
  other: number;
}

export interface IngestionQueueMetrics {
  name: string | null;
  pending: number | null;
  recent_enqueued: number;
  recent_processed: number;
}

export interface IngestionMetrics {
  documents: IngestionDocuments;
  queue: IngestionQueueMetrics;
}

export interface MemoryMetrics {
  active_sessions: number;
  avg_turns: number | null;
}

export interface MetricsOverview {
  window_seconds: number;
  http: HttpMetrics;
  graph: GraphMetrics;
  tokens: TokenMetrics;
  ingestion: IngestionMetrics;
  memory: MemoryMetrics;
}
