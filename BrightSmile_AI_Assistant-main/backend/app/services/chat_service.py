from datetime import datetime, timezone

from app.models.schemas import Citation, ChatMessage, ChatRequest, ChatResponse
from app.services.image_annotation import (
    crop_to_finding,
    draw_annotated_image,
    find_mentioned_findings,
    select_single_finding,
    to_data_url,
    wants_zoom,
)
from app.services.llm.base import LLMClient
from app.services.rag.retriever import Retriever
from app.storage.interface import CaseStorage

EXTENSION_MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}


class CaseNotFoundError(Exception):
    pass


class ChatService:
    def __init__(self, storage: CaseStorage, llm_client: LLMClient, retriever: Retriever | None = None):
        self._storage = storage
        self._llm_client = llm_client
        self._retriever = retriever

    async def ask(self, case_id: str, request: ChatRequest) -> ChatResponse:
        record = self._storage.load_case_record(case_id)
        if record is None:
            raise CaseNotFoundError(case_id)

        image_path = self._storage.get_original_image_path(case_id)
        if image_path is None:
            raise CaseNotFoundError(case_id)

        media_type = EXTENSION_MEDIA_TYPES.get(image_path.suffix.lower(), "image/jpeg")
        image_bytes = image_path.read_bytes()

        findings_context = self._build_findings_context(record)
        history = self._storage.load_chat_history(case_id)

        retrieved_chunks = None
        if self._retriever is not None:
            retrieved_chunks = self._retrieve_for_case(request.message, record)

        reply = await self._llm_client.chat(
            image_bytes=image_bytes,
            image_media_type=media_type,
            findings_context=findings_context,
            history=history,
            user_message=request.message,
            retrieved_chunks=retrieved_chunks,
        )

        now = datetime.now(timezone.utc).isoformat()
        history = history + [
            ChatMessage(role="user", content=request.message, created_at=now),
            ChatMessage(role="assistant", content=reply, created_at=now),
        ]
        self._storage.save_chat_history(case_id, history)

        citations = [
            Citation(chunk_id=c.chunk_id, source=c.source, url=c.url)
            for c in (retrieved_chunks or [])
        ]

        # If the reply names a detected condition, render the real YOLO
        # bounding box(es) onto the image server-side and send it back --
        # the LLM never touches pixels, it can't produce accurate coordinates.
        annotated_image = None
        combined_text = f"{request.message} {reply}"
        mentioned = find_mentioned_findings(combined_text, record.original_findings)
        if mentioned:
            if wants_zoom(request.message):
                target = select_single_finding(combined_text, mentioned, record.image_dimensions)
                annotated_bytes = crop_to_finding(image_bytes, target) if target else draw_annotated_image(
                    image_bytes, mentioned
                )
            else:
                annotated_bytes = draw_annotated_image(image_bytes, mentioned)
            annotated_image = to_data_url(annotated_bytes)

        return ChatResponse(reply=reply, citations=citations, annotated_image=annotated_image)

    def get_history(self, case_id: str) -> list[ChatMessage]:
        if self._storage.load_case_record(case_id) is None:
            raise CaseNotFoundError(case_id)
        return self._storage.load_chat_history(case_id)

    def clear_history(self, case_id: str) -> None:
        if self._storage.load_case_record(case_id) is None:
            raise CaseNotFoundError(case_id)
        self._storage.save_chat_history(case_id, [])

    def _retrieve_for_case(self, user_message: str, record):
        """Retrieves both for the user's actual question and, separately,
        for each distinct detected condition -- a single blended query biases
        toward whichever condition dominates the phrasing, so a case with
        both caries and impacted teeth would silently under-cover one of
        them. Querying per-condition then merging (deduped, best score wins)
        ensures every detected disease gets its own grounded lookup instead
        of riding on the coattails of the user's wording."""
        conditions = sorted({f.condition.replace("_", " ") for f in record.original_findings})

        queries = [self._build_retrieval_query(user_message, conditions)]
        queries += [f"{c} diagnosis management ADA guideline" for c in conditions]

        merged: dict[str, object] = {}
        for query in queries:
            for chunk in self._retriever.retrieve(query, k=3):
                existing = merged.get(chunk.chunk_id)
                if existing is None or chunk.score > existing.score:
                    merged[chunk.chunk_id] = chunk

        ranked = sorted(merged.values(), key=lambda c: c.score, reverse=True)
        return ranked[:6]

    @staticmethod
    def _build_retrieval_query(user_message: str, conditions: list[str]) -> str:
        if not conditions:
            return user_message
        return f"{user_message} (detected conditions: {', '.join(conditions)})"

    @staticmethod
    def _build_findings_context(record) -> str:
        if not record.original_findings:
            return "No findings were detected above the confidence threshold."
        lines = []
        for f in record.original_findings:
            lines.append(
                f"- {f.condition} (confidence {f.confidence:.2f}): {f.clinical_message}"
            )
        return "\n".join(lines)
