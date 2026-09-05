import os
from openai import OpenAI

_client: OpenAI | None = None
_MODEL = "text-embedding-3-small"
_DIMS = 1536


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _client


def embed(texts: list[str]) -> list[list[float]]:
    """Return one 1536-dim vector per input string."""
    if not texts:
        return []
    resp = _get_client().embeddings.create(input=texts, model=_MODEL)
    resp.data.sort(key=lambda x: x.index)
    return [item.embedding for item in resp.data]


def embed_one(text: str) -> list[float]:
    return embed([text])[0]
