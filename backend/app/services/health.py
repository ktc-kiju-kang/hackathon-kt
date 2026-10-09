import logging
import subprocess
import time
from datetime import UTC, datetime
from functools import lru_cache
from typing import Literal

from app.agent.providers import get_provider
from app.core.config import settings
from app.core.db import get_db
from app.schemas.health import Health

log = logging.getLogger(__name__)

_STARTED_AT = time.monotonic()  # 모듈 import 시각 = 서버 프로세스 시작 기준 (단조 시계)


def check_db() -> Literal["ok", "error"]:
    """PostgreSQL 연결과 마이그레이션 적용 확인."""
    try:
        with get_db() as db:
            db.execute("select version from schema_migrations limit 1").fetchall()
        return "ok"
    except Exception as e:  # 접속 실패·마이그레이션 오류 모두 error (health 자체는 200 유지)
        log.warning("db health check failed: %s", e)
        return "error"


@lru_cache
def _git_sha() -> str | None:
    """실행 중인 소스의 커밋 SHA. 시험 결과에 SHA를 남길 때 쓴다 (git이 없으면 None)."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=2, check=True
        )
        return out.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def _llm_name() -> str | None:
    try:
        return get_provider().name
    except Exception:  # 잘못된 LLM_PROVIDER여도 health는 살아 있어야 한다
        log.warning("LLM provider misconfigured", exc_info=True)
        return None


def get_health() -> Health:
    llm = _llm_name()
    return Health(
        status="ok",
        time=datetime.now(UTC),
        version=settings.app_version or _git_sha(),
        db=check_db(),
        llm=llm,
        llm_mode=None if llm is None else "mock" if llm == "mock" else "real",
        uptime_seconds=max(0, int(time.monotonic() - _STARTED_AT)),
    )
