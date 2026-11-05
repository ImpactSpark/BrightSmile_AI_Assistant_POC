from abc import ABC, abstractmethod

from app.models.schemas import RetrievedChunk


class RagIndex(ABC):
    """Storage interface for the RAG chunk index.

    Kept abstract, mirroring CaseStorage, so a local/embedded backend can be
    swapped in for pgvector without changing callers.
    """

    @abstractmethod
    def upsert_chunks(self, chunks: list[RetrievedChunk], embeddings: list[list[float]]) -> None:
        ...

    @abstractmethod
    def search_dense(
        self, query_embedding: list[float], k: int, condition_filter: str | None = None
    ) -> list[RetrievedChunk]:
        ...

    @abstractmethod
    def search_sparse(
        self, query: str, k: int, condition_filter: str | None = None
    ) -> list[RetrievedChunk]:
        ...

    @abstractmethod
    def delete_source(self, source: str) -> None:
        ...
