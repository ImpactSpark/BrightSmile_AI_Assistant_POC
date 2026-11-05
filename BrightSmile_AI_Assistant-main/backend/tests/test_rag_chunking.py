from app.services.rag.chunking import chunk_document


def test_chunk_document_keeps_short_text_as_one_chunk():
    text = "A short recommendation about caries management."
    chunks = chunk_document(text, max_tokens=400, overlap_tokens=50)
    assert chunks == [text]


def test_chunk_document_splits_long_text_on_sentence_boundaries():
    sentence = "This is a clinical recommendation sentence about dental caries. "
    text = sentence * 200
    chunks = chunk_document(text, max_tokens=100, overlap_tokens=20)
    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.strip()


def test_chunk_document_splits_on_headers():
    text = "Caries Management\nManage caries by X.\n\nPeriodontal Care\nManage gums by Y."
    chunks = chunk_document(text, max_tokens=400, overlap_tokens=50)
    assert len(chunks) == 2
    assert "Caries" in chunks[0]
    assert "Periodontal" in chunks[1]


def test_chunk_document_merges_bare_heading_fragments():
    # Title-page-style text: short heading-only lines with no sentence
    # punctuation get isolated by header-detection; they should merge into
    # the next real prose chunk instead of surfacing as near-empty chunks.
    text = "Practice Guidelines\nAmerican Dental Association\nSection One is a real sentence about caries."
    chunks = chunk_document(text, max_tokens=400, overlap_tokens=50)
    assert len(chunks) == 1
    assert "Practice Guidelines" in chunks[0]
    assert "real sentence about caries" in chunks[0]
