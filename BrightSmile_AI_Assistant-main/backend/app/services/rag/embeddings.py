from functools import lru_cache

from sentence_transformers import SentenceTransformer


class EmbeddingModel:
    """Local embedding model wrapper -- no per-query API cost/latency, and
    corpus/query text never leaves infra (relevant since this feeds patient
    chat, even though the corpus itself is public guideline text)."""

    def __init__(self, model_name: str):
        self._model = SentenceTransformer(model_name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self._model.encode(texts, normalize_embeddings=True).tolist()

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]


@lru_cache
def get_embedding_model(model_name: str) -> EmbeddingModel:
    return EmbeddingModel(model_name)
