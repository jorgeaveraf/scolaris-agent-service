CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS authorized_users (
  email TEXT PRIMARY KEY,
  google_sub TEXT UNIQUE,
  display_name TEXT,
  role TEXT NOT NULL CHECK (role IN ('chat', 'viewer', 'curator', 'admin')),
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE authorized_users ADD COLUMN IF NOT EXISTS display_name TEXT;

CREATE TABLE IF NOT EXISTS chat_history (
  id UUID PRIMARY KEY,
  actor_email TEXT,
  question TEXT NOT NULL,
  answer TEXT NOT NULL,
  sources JSONB NOT NULL DEFAULT '[]'::jsonb,
  is_evaluation BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE chat_history ADD COLUMN IF NOT EXISTS is_evaluation BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_chat_history_created_at ON chat_history (created_at DESC);

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
  source_url TEXT,
  uploaded_by_email TEXT,
  uploaded_by_name TEXT,
  doc_id TEXT REFERENCES documents(doc_id) ON DELETE SET NULL,
  upload_path TEXT NOT NULL,
  chunks_count INT DEFAULT 0,
  last_ingested_at TIMESTAMP,
  error_msg TEXT,
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now()
);

ALTER TABLE raw_documents ADD COLUMN IF NOT EXISTS source_url TEXT;
ALTER TABLE raw_documents ADD COLUMN IF NOT EXISTS uploaded_by_email TEXT;
ALTER TABLE raw_documents ADD COLUMN IF NOT EXISTS uploaded_by_name TEXT;

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
