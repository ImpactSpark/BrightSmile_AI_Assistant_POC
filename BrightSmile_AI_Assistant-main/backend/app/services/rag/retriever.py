from app.models.schemas import RetrievedChunk
from app.services.rag.embeddings import EmbeddingModel
from app.services.rag.hybrid import reciprocal_rank_fusion
from app.services.rag.reranker import Reranker
from app.storage.rag_interface import RagIndex


class Retriever:
    """Hybrid BM25 (sparse) + dense retrieval fused via Reciprocal Rank
    Fusion, then optionally cross-encoder reranked. Dense alone under-retrieves
    exact clinical terms (drug names, CDT codes); BM25 alone misses paraphrase
    queries -- fusing both is the standard low-effort/high-lift combination.
    The reranker (if provided) narrows the fused fanout candidates down to a
    small, precisely-ordered set for the LLM context."""

    def __init__(
        self,
        index: RagIndex,
        embedding_model: EmbeddingModel,
        reranker: Reranker | None = None,
        fanout: int = 20,
    ):
        self._index = index
        self._embedding_model = embedding_model
        self._reranker = reranker
        self._fanout = fanout

    def retrieve(
        self, query: str, k: int, condition_filter: str | None = None
    ) -> list[RetrievedChunk]:
        query_embedding = self._embedding_model.embed_one(query)
        dense_results = self._index.search_dense(query_embedding, self._fanout, condition_filter)
        sparse_results = self._index.search_sparse(query, self._fanout, condition_filter)
        fused = reciprocal_rank_fusion(
            dense_results, sparse_results, k if self._reranker is None else self._fanout
        )
        if self._reranker is None:
            return fused[:k]
        return self._reranker.rerank(query, fused, top_k=k)
