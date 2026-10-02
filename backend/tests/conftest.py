import pytest

from app.agent.providers.mock import MockProvider
from app.config import settings
from app.services import rate_limit
from app.services.chat_store import MemoryChatStore


@pytest.fixture(autouse=True)
def isolate_external(monkeypatch):
    """로컬 .env에 실제 키가 있어도 테스트는 실제 LLM·DB에 붙지 않는다."""
    monkeypatch.setattr(settings, "anthropic_api_key", "")
    monkeypatch.setattr(settings, "gemini_api_key", "")
    monkeypatch.setattr(settings, "supabase_url", "")
    monkeypatch.setattr("app.agent.loop.get_provider", lambda: MockProvider())
    rate_limit.reset()
    store = MemoryChatStore()
    monkeypatch.setattr("app.services.chat.get_chat_store", lambda: store)
    return store


@pytest.fixture
def use_provider():
    """radar·product 요청이 쓸 LLM을 고정한다 (FastAPI 의존성 override — 모듈 패치 없음)."""
    from app.agent.stages import llm_provider
    from app.main import app

    def use(provider) -> None:
        app.dependency_overrides[llm_provider] = lambda: provider

    yield use
    app.dependency_overrides.pop(llm_provider, None)


@pytest.fixture
def mock_llm(use_provider):
    use_provider(MockProvider())
