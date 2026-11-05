from app.models.schemas import RetrievedChunk

TRUST_WEIGHT = {
    "ada_guideline": 1.15,
    "pubmed": 1.0,
    "general": 0.9,
}

RRF_K = 60


def reciprocal_rank_fusion(
    dense_results: list[RetrievedChunk], sparse_results: list[RetrievedChunk], k: int
) -> list[RetrievedChunk]:
    """Fuses dense + sparse rankings via Reciprocal Rank Fusion -- avoids
    tuning a blend weight between two differently-scaled score distributions,
    the standard low-effort/high-lift hybrid retrieval strategy."""
    scores: dict[str, float] = {}
    chunks_by_id: dict[str, RetrievedChunk] = {}

    for results in (dense_results, sparse_results):
        for rank, chunk in enumerate(results):
            scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0.0) + 1.0 / (RRF_K + rank + 1)
            chunks_by_id[chunk.chunk_id] = chunk

    for chunk_id, chunk in chunks_by_id.items():
        scores[chunk_id] *= TRUST_WEIGHT.get(chunk.doc_type, 1.0)

    ranked_ids = sorted(scores, key=lambda cid: scores[cid], reverse=True)[:k]
    return [
        chunks_by_id[cid].model_copy(update={"score": scores[cid]}) for cid in ranked_ids
    ]
