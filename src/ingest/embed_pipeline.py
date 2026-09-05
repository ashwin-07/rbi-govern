"""
Chunk all documents in the DB and embed them via OpenAI.

Run once (safe to re-run — ON CONFLICT DO NOTHING prevents duplicates):
    python -m src.ingest.embed_pipeline
    python -m src.ingest.embed_pipeline --strategy clause   # single strategy
"""

import argparse
from src.db import get_documents, insert_chunks
from src.chunk import fixed_size, recursive, clause_hierarchy, Chunk
from src.embed import embed
from src.logger import get_logger

log = get_logger("rbi_govern.embed_pipeline")

_STRATEGIES = {
    "fixed": fixed_size,
    "recursive": recursive,
    "clause": clause_hierarchy,
}

_EMBED_BATCH = 100  # OpenAI allows up to 2048 inputs per call; 100 keeps payloads small


def _chunk_doc(doc: dict, strategy: str) -> list[Chunk]:
    text = doc["raw_text"] or ""
    if not text.strip():
        log.warning("doc id=%s has no raw_text, skipping", doc["id"])
        return []
    return _STRATEGIES[strategy](text)


def run(strategies: list[str]) -> None:
    docs = get_documents()
    log.info("Loaded %d documents", len(docs))

    for strategy in strategies:
        log.info("--- Strategy: %s ---", strategy)
        all_chunks: list[dict] = []

        for doc in docs:
            chunks = _chunk_doc(doc, strategy)
            for c in chunks:
                all_chunks.append({
                    "document_id": doc["id"],
                    "chunk_index": c.chunk_index,
                    "strategy": c.strategy,
                    "chunk_text": c.text,
                    "token_count": len(c.text) // 4,  # rough approximation
                    "content_vector": None,             # filled below
                    "_text": c.text,                   # temp key for batching
                })

        log.info("  %d chunks generated", len(all_chunks))

        # Embed in batches
        texts = [c["_text"] for c in all_chunks]
        vectors: list[list[float]] = []
        for i in range(0, len(texts), _EMBED_BATCH):
            batch = texts[i : i + _EMBED_BATCH]
            vectors.extend(embed(batch))
            log.debug("  Embedded batch %d/%d", i // _EMBED_BATCH + 1, -(-len(texts) // _EMBED_BATCH))

        for chunk, vector in zip(all_chunks, vectors):
            chunk["content_vector"] = vector
            del chunk["_text"]

        insert_chunks(all_chunks)
        log.info("  %d chunks inserted (duplicates skipped)", len(all_chunks))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--strategy",
        choices=list(_STRATEGIES),
        help="Run a single strategy (default: all three)",
    )
    args = parser.parse_args()

    chosen = [args.strategy] if args.strategy else list(_STRATEGIES)
    run(chosen)
