CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS documents (
    id          SERIAL PRIMARY KEY,
    circular_number TEXT,
    issue_date  DATE,
    title       TEXT NOT NULL,
    category    TEXT,
    raw_text    TEXT,
    source_url  TEXT UNIQUE NOT NULL,
    source_page TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS llm_calls (
    id                  SERIAL PRIMARY KEY,
    model               TEXT        NOT NULL,
    purpose             TEXT,
    prompt_tokens       INTEGER     NOT NULL,
    completion_tokens   INTEGER     NOT NULL,
    cost_usd            NUMERIC(10, 6) NOT NULL,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);
