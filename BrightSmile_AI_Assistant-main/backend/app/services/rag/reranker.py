from functools import lru_cache

from sentence_transformers import CrossEncoder

from app.models.schemas import RetrievedChunk


class Reranker:
    """Cross-encoder reranks a small hybrid-retrieved candidate set.

    Bi-encoders (dense embeddings) score query and doc independently then
    compare vectors -- cheap enough to run over the whole corpus, but query
    and doc never attend to each other, so relevance is coarse. Cross-encoders
    jointly encode (query, doc) pairs for much better precision, but cost
    scales per-pair so can't run over the full corpus -- hence retrieve
    broadly and cheaply (hybrid), then rerank narrowly and expensively (here)."""

    def __init__(self, model_name: str):
        self._model = CrossEncoder(model_name)

    def rerank(self, query: str, chunks: list[RetrievedChunk], top_k: int) -> list[RetrievedChunk]:
        if not chunks:
            return []
        pairs = [(query, c.text) for c in chunks]
        scores = self._model.predict(pairs)
        ranked = sorted(zip(chunks, scores), key=lambda pair: pair[1], reverse=True)[:top_k]
        return [c.model_copy(update={"score": float(s)}) for c, s in ranked]


@lru_cache
def get_reranker(model_name: str) -> Reranker:
    return Reranker(model_name)
