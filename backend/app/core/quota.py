"""단순 메모리 기반 사용량 제한. 공개 데모 API가 LLM 비용을 무제한으로 쓰지 않게 한다.

서버 프로세스 하나 기준이다. 여러 인스턴스로 늘리면 DB/Redis 기반으로 바꿔야 한다.
"""

import ipaddress
import time
from collections import defaultdict, deque
from datetime import UTC, datetime
from typing import TypedDict

from fastapi import HTTPException, Request

from app.core.config import settings


class _Daily(TypedDict):
    day: str
    count: int


_WINDOW = 600.0
_hits: dict[str, deque[float]] = defaultdict(deque)
_daily: _Daily = {"day": "", "count": 0}
_SWEEP_AT = 1000  # 키가 이만큼 쌓이면 오래된 기록을 정리한다


def _valid_ip(value: str) -> str | None:
    try:
        return str(ipaddress.ip_address(value.strip()))
    except ValueError:
        return None


def client_ip(request: Request) -> str:
    """사용량 한도용 클라이언트 IP. 클라이언트가 바꿀 수 있는 값을 쓰지 않는다.

    - `CF-Connecting-IP`: Cloudflare 같은 앞단 프록시가 실제 방문자 IP로 **항상 덮어쓴다** → 우선.
      `True-Client-IP`는 zone 설정이 켜져 있을 때만 덮어쓴다. 꺼져 있으면 클라이언트 값이
      그대로 통과하므로 쓰지 않는다.
    - 없으면 `X-Forwarded-For`의 **마지막 값**(가장 가까운 프록시가 붙인 값). 첫 값은 클라이언트가
      넣을 수 있다. 최악의 경우 프록시 단위로 묶여 한도가 거칠어질 뿐 우회되지 않는다.
    - 둘 다 없으면(로컬·테스트) 직접 연결한 주소. IP 형식이 아닌 값은 버린다.
    """
    if ip := _valid_ip(request.headers.get("cf-connecting-ip", "")):
        return ip
    hops = [h for h in request.headers.get("x-forwarded-for", "").split(",") if h.strip()]
    if hops and (ip := _valid_ip(hops[-1])):
        return ip
    return request.client.host if request.client else "unknown"


def _quota_key(ip: str) -> str:
    """IPv6는 /64 대역으로 묶는다 (한 사용자가 주소를 바꿔 가며 한도를 피하지 못하게)."""
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return ip
    if addr.version == 6:
        return str(ipaddress.ip_network(f"{addr}/64", strict=False))
    return ip


def _sweep(now: float) -> None:
    """창(10분)이 지난 기록만 남은 키를 지운다 (서로 다른 IP가 많아도 메모리가 늘지 않게)."""
    for key in [k for k, q in _hits.items() if not q or now - q[-1] > _WINDOW]:
        del _hits[key]


def check_quota(ip: str) -> None:
    now = time.monotonic()
    if len(_hits) > _SWEEP_AT:
        _sweep(now)
    key = _quota_key(ip)
    q = _hits[key]
    while q and now - q[0] > _WINDOW:
        q.popleft()
    if len(q) >= settings.chat_rate_per_ip:
        raise HTTPException(
            status_code=429, detail="잠시 후 다시 시도하세요 (요청이 너무 많습니다)"
        )

    today = datetime.now(UTC).strftime("%Y-%m-%d")
    if _daily["day"] != today:
        _daily["day"], _daily["count"] = today, 0
    if _daily["count"] >= settings.chat_daily_limit:
        if not q:
            del _hits[key]
        raise HTTPException(status_code=429, detail="오늘 사용량 한도에 도달했습니다")

    q.append(now)
    _daily["count"] += 1


def reset() -> None:  # 테스트용
    _hits.clear()
    _daily["day"], _daily["count"] = "", 0
