CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS chunks (
    id              SERIAL PRIMARY KEY,
    document_id     INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index     INTEGER NOT NULL,
    strategy        TEXT NOT NULL,   -- 'fixed' | 'recursive' | 'clause'
    chunk_text      TEXT NOT NULL,
    token_count     INTEGER,
    content_vector  vector(1536),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (document_id, chunk_index, strategy)
);

-- HNSW index: graph-based ANN search.
-- m=16: connections per node (higher → better recall, more memory).
-- ef_construction=64: candidate list size during build (higher → better recall, slower build).
-- vector_cosine_ops: cosine similarity — correct for OpenAI's normalized output vectors.
CREATE INDEX IF NOT EXISTS chunks_hnsw_idx
    ON chunks USING hnsw (content_vector vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- GIN index for BM25-style full-text search (the sparse side of hybrid retrieval).
CREATE INDEX IF NOT EXISTS chunks_fts_idx
    ON chunks USING gin (to_tsvector('english', chunk_text));
