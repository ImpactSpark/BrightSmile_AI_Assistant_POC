import json
from dataclasses import dataclass
from pathlib import Path

from app.services.rag.retriever import Retriever


@dataclass
class EvalCase:
    query: str
    expected_chunk_ids: list[str]


@dataclass
class EvalResult:
    recall_at_k: float
    mrr: float
    per_query: list[dict]


def load_eval_set(path: Path) -> list[EvalCase]:
    data = json.loads(path.read_text())
    return [EvalCase(query=d["query"], expected_chunk_ids=d["expected_chunk_ids"]) for d in data]


def evaluate_retriever(retriever: Retriever, eval_cases: list[EvalCase], k: int) -> EvalResult:
    """Recall@k and MRR against a labeled (query -> expected chunk ids) set.
    Numbers here are the only source of truth for whether hybrid/rerank are
    worth their added complexity on this corpus -- never estimate them."""
    recalls = []
    reciprocal_ranks = []
    per_query = []

    for case in eval_cases:
        if not case.expected_chunk_ids:
            continue
        results = retriever.retrieve(case.query, k=k)
        retrieved_ids = [c.chunk_id for c in results]

        hit = any(cid in retrieved_ids for cid in case.expected_chunk_ids)
        recalls.append(1.0 if hit else 0.0)

        rr = 0.0
        for rank, cid in enumerate(retrieved_ids, start=1):
            if cid in case.expected_chunk_ids:
                rr = 1.0 / rank
                break
        reciprocal_ranks.append(rr)

        per_query.append(
            {"query": case.query, "hit": hit, "reciprocal_rank": rr, "retrieved_ids": retrieved_ids}
        )

    recall_at_k = sum(recalls) / len(recalls) if recalls else 0.0
    mrr = sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0.0
    return EvalResult(recall_at_k=recall_at_k, mrr=mrr, per_query=per_query)
