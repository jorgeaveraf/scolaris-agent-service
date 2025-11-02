CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
  id SERIAL PRIMARY KEY,
  doc_id TEXT UNIQUE NOT NULL,
  title TEXT,
  source TEXT,
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS raw_documents (
  id UUID PRIMARY KEY,
  filename TEXT NOT NULL,
  content_type TEXT,
  size_bytes BIGINT NOT NULL,
  checksum TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL,
  area TEXT,
  role TEXT,
  vigencia TEXT,
  doc_id TEXT REFERENCES documents(doc_id) ON DELETE SET NULL,
  upload_path TEXT NOT NULL,
  chunks_count INT DEFAULT 0,
  last_ingested_at TIMESTAMP,
  error_msg TEXT,
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_raw_documents_status ON raw_documents (status);
CREATE INDEX IF NOT EXISTS idx_raw_documents_area ON raw_documents (area);
CREATE INDEX IF NOT EXISTS idx_raw_documents_role ON raw_documents (role);

CREATE TABLE IF NOT EXISTS chunks (
  id BIGSERIAL PRIMARY KEY,
  doc_id TEXT NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
  chunk_no INT NOT NULL,
  content TEXT NOT NULL,
  metadata JSONB,
  embedding vector(1536)
);

CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks (doc_id);
CREATE INDEX IF NOT EXISTS idx_chunks_meta ON chunks USING GIN (metadata);
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
