from functools import lru_cache

from app.config import settings

from .base import LLMProvider


@lru_cache
def get_provider() -> LLMProvider:
    """LLM_PROVIDER 설정으로 어댑터 선택.

    비우면 키로 자동 선택: ANTHROPIC_API_KEY → anthropic, GEMINI_API_KEY → gemini, 없으면 mock.
    """
    name = settings.llm_provider or (
        "anthropic"
        if settings.anthropic_api_key
        else "gemini"
        if settings.gemini_api_key
        else "mock"
    )
    if name == "anthropic":
        from .anthropic import AnthropicProvider

        return AnthropicProvider()
    if name in ("gemini", "openai"):
        from .openai_compat import OpenAICompatProvider

        return OpenAICompatProvider(preset=name)
    if name == "mock":
        from .mock import MockProvider

        return MockProvider()
    raise ValueError(f"알 수 없는 LLM_PROVIDER: {name}")


__all__ = ["LLMProvider", "get_provider"]
