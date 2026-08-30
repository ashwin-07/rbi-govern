-- Recreate documents with fixed-width columns first so Postgres can compute
-- their offsets without scanning variable-width data.
-- Column order: fixed-size → short text → long text (raw_text last).

CREATE TABLE documents_new (
    id              SERIAL PRIMARY KEY,
    created_at      TIMESTAMPTZ DEFAULT NOW(),   -- 8-byte fixed
    issue_date      DATE,                         -- 4-byte fixed
    circular_number TEXT,
    title           TEXT NOT NULL,
    category        TEXT,
    source_page     TEXT,
    source_url      TEXT UNIQUE NOT NULL,
    raw_text        TEXT
);

INSERT INTO documents_new (id, created_at, issue_date, circular_number, title, category, source_page, source_url, raw_text)
SELECT                      id, created_at, issue_date, circular_number, title, category, source_page, source_url, raw_text
FROM documents;

DROP TABLE documents;
ALTER TABLE documents_new RENAME TO documents;

-- Short text: MAIN = compress but keep inline (they're small enough to stay on the heap page)
ALTER TABLE documents ALTER COLUMN circular_number SET STORAGE MAIN;
ALTER TABLE documents ALTER COLUMN title           SET STORAGE MAIN;
ALTER TABLE documents ALTER COLUMN category        SET STORAGE MAIN;
ALTER TABLE documents ALTER COLUMN source_page     SET STORAGE MAIN;
ALTER TABLE documents ALTER COLUMN source_url      SET STORAGE MAIN;

-- raw_text: EXTENDED = compress + out-of-line (already the default, but explicit)
ALTER TABLE documents ALTER COLUMN raw_text SET STORAGE EXTENDED;
