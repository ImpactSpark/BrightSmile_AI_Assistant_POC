import re

HEADER_PATTERN = re.compile(r"\n(?=[A-Z][A-Za-z0-9 ,/&-]{3,80}\n)")
SENTENCE_PATTERN = re.compile(r"(?<=[.!?])\s+")


def _estimate_tokens(text: str) -> int:
    # ~4 chars/token is a standard rough estimate for English text; avoids
    # pulling in a tokenizer dependency just for chunk sizing.
    return max(1, len(text) // 4)


def _split_to_token_budget(text: str, max_tokens: int, overlap_tokens: int) -> list[str]:
    sentences = SENTENCE_PATTERN.split(text.strip())
    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0

    for sentence in sentences:
        sentence_tokens = _estimate_tokens(sentence)
        if current and current_tokens + sentence_tokens > max_tokens:
            chunks.append(" ".join(current))
            overlap: list[str] = []
            overlap_count = 0
            for s in reversed(current):
                overlap_count += _estimate_tokens(s)
                overlap.insert(0, s)
                if overlap_count >= overlap_tokens:
                    break
            current = overlap
            current_tokens = overlap_count
        current.append(sentence)
        current_tokens += sentence_tokens

    if current:
        chunks.append(" ".join(current))
    return chunks


MIN_CHUNK_TOKENS = 15


def _looks_like_bare_heading(chunk: str) -> bool:
    """True for fragments with no sentence-ending punctuation -- these are
    almost always title/heading lines that header-detection isolated rather
    than real prose sections, common in title-page/table-heavy PDFs."""
    return not re.search(r"[.!?]", chunk)


def _merge_small_chunks(chunks: list[str], max_tokens: int, min_tokens: int) -> list[str]:
    """Merges heading-only fragments under the token floor into the next
    chunk, so retrieval doesn't surface near-empty title fragments. Leaves
    genuinely short prose sections (which end in punctuation) untouched."""
    merged: list[str] = []
    pending_heading = ""
    for chunk in chunks:
        if _estimate_tokens(chunk) < min_tokens and _looks_like_bare_heading(chunk):
            pending_heading = f"{pending_heading}\n{chunk}" if pending_heading else chunk
            continue
        combined = f"{pending_heading}\n{chunk}" if pending_heading else chunk
        pending_heading = ""
        merged.append(combined)
    if pending_heading:
        if merged:
            merged[-1] = f"{merged[-1]}\n{pending_heading}"
        else:
            merged.append(pending_heading)
    return merged


def chunk_document(text: str, max_tokens: int = 400, overlap_tokens: int = 50) -> list[str]:
    """Structure-aware chunking: split on header-like lines first (so a
    recommendation's section stays together), then recursively split any
    section still over budget on sentence boundaries with overlap. A final
    pass merges undersized fragments into their neighbor."""
    sections = [s.strip() for s in HEADER_PATTERN.split(text) if s.strip()]
    if not sections:
        sections = [text.strip()]

    chunks: list[str] = []
    for section in sections:
        if _estimate_tokens(section) <= max_tokens:
            chunks.append(section)
        else:
            chunks.extend(_split_to_token_budget(section, max_tokens, overlap_tokens))
    chunks = [c for c in chunks if c.strip()]
    return _merge_small_chunks(chunks, max_tokens, min_tokens=MIN_CHUNK_TOKENS)
