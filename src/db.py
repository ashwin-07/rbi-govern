import os
import psycopg2
from psycopg2.extras import RealDictCursor

DSN = os.environ.get("DATABASE_URL", "postgresql://localhost/rbi_govern")


def get_conn():
    return psycopg2.connect(DSN)


def migrate():
    sql_path = os.path.join(os.path.dirname(__file__), "..", "migrations", "001_initial.sql")
    with open(sql_path) as f:
        sql = f.read()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)


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
