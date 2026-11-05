from app.models.schemas import RetrievedChunk
from app.services.rag.hybrid import reciprocal_rank_fusion


def _chunk(chunk_id: str, doc_type: str = "ada_guideline") -> RetrievedChunk:
    return RetrievedChunk(chunk_id=chunk_id, text="t", source="s", doc_type=doc_type)


def test_fusion_ranks_chunk_present_in_both_lists_highest():
    dense = [_chunk("a"), _chunk("b"), _chunk("c")]
    sparse = [_chunk("b"), _chunk("d"), _chunk("a")]
    result = reciprocal_rank_fusion(dense, sparse, k=4)
    ids = [c.chunk_id for c in result]
    assert ids[0] in ("a", "b")
    assert set(ids) == {"a", "b", "c", "d"}


def test_fusion_respects_k_limit():
    dense = [_chunk("a"), _chunk("b"), _chunk("c")]
    sparse = [_chunk("d"), _chunk("e")]
    result = reciprocal_rank_fusion(dense, sparse, k=2)
    assert len(result) == 2


def test_fusion_trust_weights_ada_over_general():
    dense = [_chunk("ada", doc_type="ada_guideline")]
    sparse = [_chunk("general", doc_type="general")]
    result = reciprocal_rank_fusion(dense, sparse, k=2)
    assert result[0].chunk_id == "ada"
