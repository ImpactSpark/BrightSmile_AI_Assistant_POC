from app.models.schemas import RetrievedChunk
from app.services.rag.reranker import Reranker


def _chunk(chunk_id: str, text: str) -> RetrievedChunk:
    return RetrievedChunk(chunk_id=chunk_id, text=text, source="s", doc_type="ada_guideline")


def test_rerank_orders_by_model_score(monkeypatch):
    reranker = Reranker.__new__(Reranker)  # skip loading a real CrossEncoder model

    class FakeModel:
        def predict(self, pairs):
            # score higher for pairs whose doc text contains "match"
            return [1.0 if "match" in doc else 0.0 for _, doc in pairs]

    reranker._model = FakeModel()

    chunks = [_chunk("a", "unrelated text"), _chunk("b", "match text"), _chunk("c", "unrelated text")]
    result = reranker.rerank("query", chunks, top_k=2)

    assert len(result) == 2
    assert result[0].chunk_id == "b"


def test_rerank_empty_input_returns_empty():
    reranker = Reranker.__new__(Reranker)
    reranker._model = None
    assert reranker.rerank("query", [], top_k=5) == []
