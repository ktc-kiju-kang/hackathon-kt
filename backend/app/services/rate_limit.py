"""단순 메모리 기반 사용량 제한. 공개 데모 API가 LLM 비용을 무제한으로 쓰지 않게 한다.

인스턴스 하나(Render free) 기준이다. 여러 인스턴스로 늘리면 DB/Redis 기반으로 바꿔야 한다.
"""

import time
from collections import defaultdict, deque
from datetime import UTC, datetime

from fastapi import HTTPException

from app.config import settings

_WINDOW = 600.0
_hits: dict[str, deque[float]] = defaultdict(deque)
_daily = {"day": "", "count": 0}


def check_chat_quota(ip: str) -> None:
    now = time.monotonic()
    q = _hits[ip]
    while q and now - q[0] > _WINDOW:
        q.popleft()
    if len(q) >= settings.chat_rate_per_ip:
        raise HTTPException(
            status_code=429, detail="잠시 후 다시 시도하세요 (요청이 너무 많습니다)"
        )

    today = datetime.now(UTC).strftime("%Y-%m-%d")
    if _daily["day"] != today:
        _daily.update(day=today, count=0)
    if _daily["count"] >= settings.chat_daily_limit:
        raise HTTPException(status_code=429, detail="오늘 사용량 한도에 도달했습니다")

    q.append(now)
    _daily["count"] += 1


def reset() -> None:  # 테스트용
    _hits.clear()
    _daily.update(day="", count=0)
