import os
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values

DSN = os.environ.get("DATABASE_URL", "postgresql://localhost/rbi_govern")


def get_conn():
    return psycopg2.connect(DSN)


def migrate():
    migrations_dir = os.path.join(os.path.dirname(__file__), "..", "migrations")
    files = sorted(f for f in os.listdir(migrations_dir) if f.endswith(".sql"))
    with get_conn() as conn:
        with conn.cursor() as cur:
            for filename in files:
                path = os.path.join(migrations_dir, filename)
                with open(path) as f:
                    cur.execute(f.read())
                print(f"  Applied {filename}")


def insert_document(doc: dict) -> int | None:
    sql = """
        INSERT INTO documents (circular_number, issue_date, title, category, raw_text, source_url, source_page)
        VALUES (%(circular_number)s, %(issue_date)s, %(title)s, %(category)s, %(raw_text)s, %(source_url)s, %(source_page)s)
        ON CONFLICT (source_url) DO NOTHING
        RETURNING id
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, doc)
            row = cur.fetchone()
            return row[0] if row else None


def get_documents() -> list[dict]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, title, raw_text FROM documents ORDER BY id")
            return [dict(r) for r in cur.fetchall()]


def insert_chunks(chunks: list[dict]) -> None:
    """Batch-insert chunks. Each dict must have:
    document_id, chunk_index, strategy, chunk_text, token_count, content_vector (list[float]).
    ON CONFLICT DO NOTHING so re-running is safe.
    """
    if not chunks:
        return
    rows = [
        (
            c["document_id"],
            c["chunk_index"],
            c["strategy"],
            c["chunk_text"],
            c["token_count"],
            c["content_vector"],
        )
        for c in chunks
    ]
    sql = """
        INSERT INTO chunks (document_id, chunk_index, strategy, chunk_text, token_count, content_vector)
        VALUES %s
        ON CONFLICT (document_id, chunk_index, strategy) DO NOTHING
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            execute_values(cur, sql, rows)


def log_llm_call(model: str, purpose: str, prompt_tokens: int, completion_tokens: int, cost_usd: float):
    sql = """
        INSERT INTO llm_calls (model, purpose, prompt_tokens, completion_tokens, cost_usd)
        VALUES (%s, %s, %s, %s, %s)
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (model, purpose, prompt_tokens, completion_tokens, cost_usd))


if __name__ == "__main__":
    migrate()
    print("Migration applied.")
