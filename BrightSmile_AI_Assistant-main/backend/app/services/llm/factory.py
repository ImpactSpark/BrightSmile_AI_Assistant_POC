from app.core.config import settings
from app.services.llm.base import LLMClient


class LLMConfigError(Exception):
    pass


def get_llm_client() -> LLMClient:
    provider = settings.llm_provider.lower()

    if provider == "anthropic":
        if not settings.anthropic_api_key:
            raise LLMConfigError(
                "BRIGHTSMILE_ANTHROPIC_API_KEY is not set but LLM_PROVIDER=anthropic"
            )
        from app.services.llm.anthropic_client import AnthropicLLMClient

        return AnthropicLLMClient(api_key=settings.anthropic_api_key, model=settings.llm_model)

    if provider == "openai":
        if not settings.openai_api_key:
            raise LLMConfigError(
                "BRIGHTSMILE_OPENAI_API_KEY is not set but LLM_PROVIDER=openai"
            )
        from app.services.llm.openai_client import OpenAILLMClient

        return OpenAILLMClient(api_key=settings.openai_api_key, model=settings.llm_model)

    if provider == "groq":
        if not settings.groq_api_key:
            raise LLMConfigError(
                "BRIGHTSMILE_GROQ_API_KEY is not set but LLM_PROVIDER=groq"
            )
        from app.services.llm.openai_client import OpenAILLMClient

        return OpenAILLMClient(
            api_key=settings.groq_api_key,
            model=settings.llm_model or "llama-3.2-90b-vision-preview",
            base_url="https://api.groq.com/openai/v1",
        )

    if provider == "openrouter":
        if not settings.openrouter_api_key:
            raise LLMConfigError(
                "BRIGHTSMILE_OPENROUTER_API_KEY is not set but LLM_PROVIDER=openrouter"
            )
        from app.services.llm.openai_client import OpenAILLMClient

        return OpenAILLMClient(
            api_key=settings.openrouter_api_key,
            model=settings.llm_model or "meta-llama/llama-3.2-11b-vision-instruct:free",
            base_url="https://openrouter.ai/api/v1",
        )

    if provider == "gemini":
        if not settings.gemini_api_key:
            raise LLMConfigError(
                "BRIGHTSMILE_GEMINI_API_KEY is not set but LLM_PROVIDER=gemini"
            )
        from app.services.llm.gemini_client import GeminiLLMClient

        return GeminiLLMClient(api_key=settings.gemini_api_key, model=settings.llm_model)

    raise LLMConfigError(f"unsupported llm_provider: {settings.llm_provider}")
