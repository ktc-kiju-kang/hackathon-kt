import base64
import json
import logging
from datetime import UTC, datetime

from app.agent.providers import get_provider
from app.core.config import settings
from app.core.db import get_supabase
from app.schemas.health import Health

log = logging.getLogger(__name__)


def key_role(key: str) -> str | None:
    """Supabase 키의 역할 (anon / service_role). 키 값 자체는 로그에 남기지 않는다."""
    if key.startswith("sb_secret_"):
        return "service_role"
    if key.startswith("sb_publishable_"):
        return "anon"
    parts = key.split(".")
    if len(parts) == 3:  # legacy JWT 키
        try:
            payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=" * (-len(parts[1]) % 4)))
            return payload.get("role")
        except ValueError:
            return None
    return None


def check_db() -> str:
    """Supabase 연결·키 확인.

    anon 키로도 RLS 테이블 조회는 '빈 결과'로 성공하므로, 조회 전에 키 역할부터 확인한다.
    """
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return "unconfigured"
    role = key_role(settings.supabase_service_role_key)
    if role != "service_role":
        log.warning("SUPABASE_SERVICE_ROLE_KEY is not a service_role key (role=%s)", role)
        return "error"
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
