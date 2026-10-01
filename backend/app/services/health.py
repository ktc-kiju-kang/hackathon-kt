import logging
from datetime import UTC, datetime

from app.agent.providers import get_provider
from app.config import settings
from app.db import get_supabase
from app.schemas.health import Health

log = logging.getLogger(__name__)


def check_db() -> str:
    """Supabase 연결·키 확인. 마이그레이션 기록 테이블을 1행 조회한다."""
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return "unconfigured"
    try:
        get_supabase().table("schema_migrations").select("version").limit(1).execute()
        return "ok"
    except Exception as e:  # 키 오류·네트워크·타임아웃 모두 error로 보고 (health 자체는 200 유지)
        log.warning("db health check failed: %s", e)
        return "error"


def _llm_name() -> str | None:
    try:
        return get_provider().name
    except Exception:  # 잘못된 LLM_PROVIDER여도 health는 살아 있어야 한다 (Render 헬스체크)
        log.warning("LLM provider misconfigured", exc_info=True)
        return None


def get_health() -> Health:
    return Health(
        status="ok",
        time=datetime.now(UTC),
        version=settings.render_git_commit or None,
        db=check_db(),
        llm=_llm_name(),
    )
