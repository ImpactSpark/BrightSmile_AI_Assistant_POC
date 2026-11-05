import base64

from anthropic import AsyncAnthropic

from app.models.schemas import ChatMessage, RetrievedChunk
from app.services.llm.base import (
    HIGHLIGHT_INSTRUCTION,
    RAG_CITATION_INSTRUCTION,
    LLMClient,
    format_retrieved_chunks,
)

DEFAULT_MODEL = "claude-sonnet-5"

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


class AnthropicLLMClient(LLMClient):
    def __init__(self, api_key: str, model: str | None = None):
        self._client = AsyncAnthropic(api_key=api_key)
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
        messages = []
        image_block = {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": image_media_type,
                "data": base64.b64encode(image_bytes).decode("ascii"),
            },
        }
        sources_text = format_retrieved_chunks(retrieved_chunks)
        user_message_with_sources = f"{sources_text}\n\n{user_message}" if sources_text else user_message
        first_user_text = f"Findings for this case:\n{findings_context}\n\n{user_message_with_sources}"
        if not history:
            messages.append(
                {"role": "user", "content": [image_block, {"type": "text", "text": first_user_text}]}
            )
        else:
            messages.append(
                {"role": "user", "content": [image_block, {"type": "text", "text": f"Findings for this case:\n{findings_context}"}]}
            )
            messages.append({"role": "assistant", "content": "Understood."})
            for h in history:
                messages.append({"role": h.role, "content": h.content})
            messages.append({"role": "user", "content": user_message_with_sources})

        response = await self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        return "".join(block.text for block in response.content if block.type == "text")
