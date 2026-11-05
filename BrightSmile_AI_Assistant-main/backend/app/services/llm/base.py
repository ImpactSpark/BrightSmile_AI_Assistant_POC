from abc import ABC, abstractmethod

from app.models.schemas import ChatMessage, RetrievedChunk


class LLMServiceUnavailableError(Exception):
    """Raised when the underlying LLM provider is temporarily overloaded/unreachable."""


HIGHLIGHT_INSTRUCTION = (
    " The viewer UI already highlights the matching finding on the X-ray "
    "automatically whenever you mention its condition name (e.g. 'deep caries', "
    "'impacted tooth') in your reply -- so when asked to 'show' or 'highlight' a "
    "finding, just name the condition naturally in your answer; never say you are "
    "unable to display or highlight it. If the dentist asks to zoom in, focus on, "
    "or get a close-up of one specific tooth/finding (especially when there are "
    "multiple findings of the same condition), acknowledge that request naturally in "
    "your reply -- the viewer crops in on that single finding automatically. If it's "
    "ambiguous which one they mean, ask them to clarify by position (left/right, "
    "upper/lower) or ordinal (first/second)."
)

RAG_CITATION_INSTRUCTION = (
    " You may also be given numbered reference sources below. Only cite a source "
    "that is explicitly listed; never invent a source or citation. If none of the "
    "given sources are relevant to the question, say so instead of citing one anyway. "
    "When reference sources are given, do not reply in paragraph form -- structure "
    "the reply as two short bullet-point sections with these exact headers: "
    "'Insights:' (what the sources say, cited by number) and 'Suggestions for doctor:' "
    "(concrete next steps for the dentist). Keep each bullet to one sentence."
)


def format_retrieved_chunks(chunks: list[RetrievedChunk] | None) -> str:
    if not chunks:
        return ""
    lines = ["Reference sources (cite by number if used):"]
    for i, c in enumerate(chunks, start=1):
        lines.append(f"[{i}] ({c.source}) {c.text}")
    return "\n".join(lines)


class LLMClient(ABC):
    @abstractmethod
    async def chat(
        self,
        *,
        image_bytes: bytes,
        image_media_type: str,
        findings_context: str,
        history: list[ChatMessage],
        user_message: str,
        retrieved_chunks: list[RetrievedChunk] | None = None,
    ) -> str:
        ...
