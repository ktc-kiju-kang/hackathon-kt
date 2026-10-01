from functools import lru_cache

from app.config import settings

from .base import LLMProvider


@lru_cache
def get_provider() -> LLMProvider:
    """LLM_PROVIDER 설정으로 어댑터 선택. 비우면 API 키가 있을 때 anthropic, 없으면 mock."""
    name = settings.llm_provider or ("anthropic" if settings.anthropic_api_key else "mock")
    if name == "anthropic":
        from .anthropic import AnthropicProvider

        return AnthropicProvider()
    if name == "mock":
        from .mock import MockProvider

        return MockProvider()
    raise ValueError(f"알 수 없는 LLM_PROVIDER: {name}")


__all__ = ["LLMProvider", "get_provider"]
