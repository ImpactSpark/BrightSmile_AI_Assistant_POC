import base64

from openai import AsyncOpenAI

from app.models.schemas import ChatMessage, RetrievedChunk
from app.services.llm.base import (
    HIGHLIGHT_INSTRUCTION,
    RAG_CITATION_INSTRUCTION,
    LLMClient,
    format_retrieved_chunks,
)

DEFAULT_MODEL = "gpt-4o"

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


class OpenAILLMClient(LLMClient):
    """Works with any OpenAI-compatible chat-completions endpoint (OpenAI itself,
    Groq, OpenRouter, etc.) by pointing base_url at that provider's API."""

    def __init__(self, api_key: str, model: str | None = None, base_url: str | None = None):
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
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
        data_url = f"data:{image_media_type};base64,{base64.b64encode(image_bytes).decode('ascii')}"

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.append(
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": data_url}},
                    {"type": "text", "text": f"Findings for this case:\n{findings_context}"},
                ],
            }
        )
        for h in history:
            messages.append({"role": h.role, "content": h.content})
        sources_text = format_retrieved_chunks(retrieved_chunks)
        user_content = f"{sources_text}\n\n{user_message}" if sources_text else user_message
        messages.append({"role": "user", "content": user_content})

        response = await self._client.chat.completions.create(
            model=self._model,
            max_tokens=1024,
            messages=messages,
        )
        return response.choices[0].message.content or ""
