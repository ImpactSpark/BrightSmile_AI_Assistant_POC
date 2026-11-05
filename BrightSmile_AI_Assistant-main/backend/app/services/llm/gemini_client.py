import asyncio

import httpx
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from app.models.schemas import ChatMessage, RetrievedChunk
from app.services.llm.base import (
    HIGHLIGHT_INSTRUCTION,
    RAG_CITATION_INSTRUCTION,
    LLMClient,
    LLMServiceUnavailableError,
    format_retrieved_chunks,
)

DEFAULT_MODEL = "gemini-2.5-flash-lite"

SYSTEM_PROMPT = (
    "You are a clinical decision-support assistant helping a dentist review a dental "
    "X-ray and its AI-detected findings. Answer questions about the image and the "
    "findings below. Never state a definitive diagnosis -- findings are possible "
    "conditions requiring dentist review, not confirmed diagnoses. "
    "Keep replies short and to the point -- a few sentences, no headers or markdown "
    "formatting, unless the dentist explicitly asks for more detail."
    + HIGHLIGHT_INSTRUCTION
    + RAG_CITATION_INSTRUCTION
)


class GeminiLLMClient(LLMClient):
    def __init__(self, api_key: str, model: str | None = None):
        self._client = genai.Client(
            api_key=api_key, http_options=types.HttpOptions(timeout=45_000)
        )
        self._model = model or DEFAULT_MODEL

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
        contents = [
            types.Part.from_bytes(data=image_bytes, mime_type=image_media_type),
            f"Findings for this case:\n{findings_context}",
        ]
        for h in history:
            contents.append(f"{h.role}: {h.content}")
        sources_text = format_retrieved_chunks(retrieved_chunks)
        if sources_text:
            contents.append(sources_text)
        contents.append(f"user: {user_message}")

        attempts = 2
        for attempt in range(1, attempts + 1):
            try:
                response = await self._client.aio.models.generate_content(
                    model=self._model,
                    contents=contents,
                    config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
                )
                return response.text or ""
            except (genai_errors.ServerError, TimeoutError, httpx.TimeoutException) as exc:
                if attempt == attempts:
                    raise LLMServiceUnavailableError(
                        "Gemini is temporarily overloaded. Please try again in a moment."
                    ) from exc
                await asyncio.sleep(1.0)
