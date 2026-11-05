from app.models.schemas import RetrievedChunk
from app.services.rag.eval import EvalCase, evaluate_retriever


class FakeRetriever:
    def __init__(self, results: list[RetrievedChunk]):
        self._results = results

    def retrieve(self, query: str, k: int, condition_filter=None):
        return self._results[:k]


def _chunk(chunk_id: str) -> RetrievedChunk:
    return RetrievedChunk(chunk_id=chunk_id, text="t", source="s", doc_type="ada_guideline")


def test_recall_and_mrr_when_expected_chunk_found_first():
    retriever = FakeRetriever([_chunk("expected"), _chunk("other")])
    cases = [EvalCase(query="q", expected_chunk_ids=["expected"])]
    result = evaluate_retriever(retriever, cases, k=2)
    assert result.recall_at_k == 1.0
    assert result.mrr == 1.0


def test_recall_and_mrr_when_expected_chunk_missing():
    retriever = FakeRetriever([_chunk("a"), _chunk("b")])
    cases = [EvalCase(query="q", expected_chunk_ids=["expected"])]
    result = evaluate_retriever(retriever, cases, k=2)
    assert result.recall_at_k == 0.0
    assert result.mrr == 0.0


def test_unlabeled_cases_are_skipped():
    retriever = FakeRetriever([_chunk("a")])
    cases = [EvalCase(query="q", expected_chunk_ids=[])]
    result = evaluate_retriever(retriever, cases, k=1)
    assert result.per_query == []
    assert result.recall_at_k == 0.0
