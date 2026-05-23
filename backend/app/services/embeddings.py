"""OpenAI embeddings wrapper.

Uses text-embedding-3-small (1536 dims) by default. Batches in groups of 100
inputs per API call to respect rate/size limits.
"""

from __future__ import annotations

from functools import lru_cache

from openai import AsyncOpenAI

from app.config import get_settings

_BATCH_SIZE = 100


@lru_cache(maxsize=1)
def _client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=get_settings().openai_api_key)


async def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    settings = get_settings()
    client = _client()
    vectors: list[list[float]] = []

    for i in range(0, len(texts), _BATCH_SIZE):
        batch = texts[i : i + _BATCH_SIZE]
        resp = await client.embeddings.create(
            model=settings.embedding_model,
            input=batch,
        )
        vectors.extend([item.embedding for item in resp.data])

    return vectors


async def embed_query(text: str) -> list[float]:
    result = await embed_texts([text])
    return result[0]
