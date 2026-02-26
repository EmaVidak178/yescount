from __future__ import annotations

from openai import OpenAI

EMBED_MODEL = "text-embedding-3-small"


def embed_text(client: OpenAI, text: str) -> list[float]:
    response = client.embeddings.create(model=EMBED_MODEL, input=text)
    return response.data[0].embedding


def embed_batch(client: OpenAI, texts: list[str], batch_size: int = 100) -> list[list[float]]:
    vectors: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = client.embeddings.create(model=EMBED_MODEL, input=batch)
        vectors.extend(item.embedding for item in response.data)
    return vectors
