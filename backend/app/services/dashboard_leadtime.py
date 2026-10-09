"""현황판 리드타임 칸 (docs/contracts/dashboard.md, #107).

Issue를 만든 시각 → 그 Issue를 닫은 PR이 머지된 시각. GitHub 현황과 따로 불러와서
이 칸이 실패해도 나머지 화면은 그대로다. 토큰은 응답·로그에 남기지 않는다.
"""

import re
import statistics
import threading
import time
from datetime import UTC, datetime
from typing import Any

from app.schemas.dashboard import LeadBucket, LeadTime
from app.services import dashboard_github as gh_service
from app.services.dashboard_github import _Api, _get

MAX_CLOSED = 100  # GitHub 한 페이지 상한 — 호출 2번(PR·Issue)으로 끝낸다
HOUR, DAY = 3600, 86400
# (이름, 이상, 미만) — 위에서 아래로 고정. 마지막은 위쪽 끝이 없다
BUCKETS: list[tuple[str, int, int | None]] = [
    ("1시간 미만", 0, HOUR),
    ("1~4시간", HOUR, 4 * HOUR),
    ("4~24시간", 4 * HOUR, DAY),
    ("1~3일", DAY, 3 * DAY),
    ("3일 이상", 3 * DAY, None),
]
_CLOSES = re.compile(r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s*:?\s+#(\d+)", re.IGNORECASE)
_BRANCH = re.compile(r"^[\w.-]+/(\d+)-")  # <type>/<이슈번호>-<설명>
_cache: dict[str, tuple[float, LeadTime]] = {}
_lock = threading.Lock()


def get_leadtime() -> LeadTime:
    t = gh_service.target()
    if t is None:
        return LeadTime(status="unconfigured", message=gh_service.UNCONFIGURED)
    repo, api, token = t
    key = f"{api}|{repo}"
    ttl = gh_service.cache_ttl(token)
    with _lock:
        hit = _cache.get(key)
        if hit and time.monotonic() - hit[0] < ttl:
            return hit[1]
        result = gh_service.call_github(
            api,
            token,
            repo,
            _fetch,
            lambda msg: LeadTime(status="error", message=msg, repo=repo),
        )
        _cache[key] = (time.monotonic(), result)
        return result


def clear_cache() -> None:
    _cache.clear()


def _fetch(gh: _Api, repo: str) -> LeadTime:
    base = f"/repos/{repo}"
    pulls = _get(
        gh, f"{base}/pulls", state="closed", sort="updated", direction="desc", per_page=MAX_CLOSED
    )
    issues = _get(
        gh, f"{base}/issues", state="closed", sort="updated", direction="desc", per_page=MAX_CLOSED
    )
    created = {
        i["number"]: _parse(i["created_at"]) for i in issues if "pull_request" not in i
    }  # issues API는 PR도 돌려준다
    seconds: list[int] = []
    for p in pulls:
        if not p.get("merged_at"):  # 머지 없이 닫힌 PR
            continue
        start = created.get(_issue_number(p))
        if start is None:  # Issue와 이어지지 않았거나 최근 100개 밖
            continue
        seconds.append(max(0, int((_parse(p["merged_at"]) - start).total_seconds())))
    return LeadTime(
        status="ok",
        repo=repo,
        fetched_at=datetime.now(UTC),
        count=len(seconds),
        median_seconds=int(statistics.median(seconds)) if seconds else None,
        buckets=[
            LeadBucket(
                label=label,
                min_seconds=low,
                max_seconds=high,
                count=sum(1 for s in seconds if s >= low and (high is None or s < high)),
            )
            for label, low, high in BUCKETS
        ],
    )


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _issue_number(pr: dict[str, Any]) -> int | None:
    """PR 본문의 `Closes #N`, 없으면 브랜치 이름 `<type>/<N>-<설명>`."""
    m = _CLOSES.search(pr.get("body") or "") or _BRANCH.match(
        (pr.get("head") or {}).get("ref", "")
    )
    return int(m[1]) if m else None
