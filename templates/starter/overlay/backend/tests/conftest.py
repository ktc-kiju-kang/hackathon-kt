import pytest

from app.agent.providers import get_provider
from app.agent.providers.mock import MockProvider
from app.core import db, quota
from app.core.config import settings
from app.services.chat_store import MemoryChatStore


@pytest.fixture(autouse=True)
def isolate_external(monkeypatch, tmp_path):
    """로컬 .env에 실제 키가 있어도 테스트는 실제 LLM에 붙지 않고, DB는 테스트마다 새 파일."""
    monkeypatch.setattr(settings, "anthropic_api_key", "")
    monkeypatch.setattr(settings, "gemini_api_key", "")
    # LLM_PROVIDER=openai 등 OpenAI 호환 설정도 비운다 (아니면 get_provider가 실제 공급자를 고른다)
    monkeypatch.setattr(settings, "llm_provider", "")
    monkeypatch.setattr(settings, "llm_api_key", "")
    monkeypatch.setattr(settings, "llm_base_url", "")
    monkeypatch.setattr(settings, "llm_model", "")
    monkeypatch.setattr(settings, "database_path", str(tmp_path / "test.db"))
    db.reset_for_tests()
    get_provider.cache_clear()  # 로컬 .env로 이미 만들어진 공급자를 버린다
    monkeypatch.setattr("app.agent.loop.get_provider", lambda: MockProvider())
    quota.reset()
    store = MemoryChatStore()
    monkeypatch.setattr("app.services.chat.get_chat_store", lambda: store)
    yield store
    get_provider.cache_clear()


@pytest.fixture
def use_provider():
    """단계형 생성 API가 쓸 LLM을 고정한다 (FastAPI 의존성 override — 모듈 패치 없음)."""
    from app.agent.stages import llm_provider
    from app.main import app

    def use(provider) -> None:
        app.dependency_overrides[llm_provider] = lambda: provider

    yield use
    app.dependency_overrides.pop(llm_provider, None)


@pytest.fixture
def mock_llm(use_provider):
    use_provider(MockProvider())
