-- Migration: create_code_chunks table with pgvector support
-- Requires pgvector extension and TimescaleDB (if hypertable needed) to be installed.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS code_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repo TEXT NOT NULL,
    path TEXT NOT NULL,
    symbol TEXT,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(256) NOT NULL,
    token_count INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Unique constraint for upserts
CREATE UNIQUE INDEX IF NOT EXISTS uq_code_chunks_repo_path_idx ON code_chunks(repo, path, chunk_index);

-- Vector index for fast ANN search (using ivfflat)
CREATE INDEX IF NOT EXISTS idx_code_chunks_embedding ON code_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Optional: add full‑text search column and GIN index if needed later.
