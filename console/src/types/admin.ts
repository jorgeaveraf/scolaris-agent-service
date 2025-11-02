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
