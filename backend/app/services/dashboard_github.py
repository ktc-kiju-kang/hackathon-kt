"""현황판 GitHub 칸 (docs/contracts/dashboard.md).

토큰은 요청 헤더에만 쓰고 응답·로그에 남기지 않는다.
"""

import logging
import re
import subprocess
import threading
import time
from datetime import UTC, datetime
from typing import Any, Literal

import httpx

from app.core.config import settings
from app.schemas.dashboard import GhClaim, GhIssue, GhPull, GhRun, GithubStatus
from app.services.dashboard import ROOT

log = logging.getLogger(__name__)

CACHE_SEC = 60  # 같은 화면을 여러 번 새로 고쳐도 GitHub 한도(토큰 없으면 시간당 60회)를 지킨다
MAX_PULLS, MAX_CLAIMS = 10, 10
_cache: dict[str, tuple[float, GithubStatus]] = {}
_transport: httpx.BaseTransport | None = None  # 테스트가 가짜 GitHub(httpx.MockTransport)를 넣는다
_lock = threading.Lock()


class GithubError(Exception):
    """사용자에게 보여 줄 수 있는 이유 (토큰 값 없음)."""


def get_github_status() -> GithubStatus:
    remote = settings.git_remote_url or _git_origin()
    repo = settings.github_repo or _repo_from_remote(remote)
    if not repo:
        return GithubStatus(
            status="unconfigured",
            message="레포를 알 수 없습니다 — backend/.env에 GITHUB_REPO=owner/name",
        )
    api = settings.github_api_url or _api_from_remote(remote)
    key = f"{api}|{repo}"
    with _lock:
        hit = _cache.get(key)
        if hit and time.monotonic() - hit[0] < CACHE_SEC:
            return hit[1]
        try:
            with _client(api) as gh:
                result = _fetch(gh, repo)
        except GithubError as e:
            result = GithubStatus(status="error", message=str(e), repo=repo)
        except httpx.HTTPError as e:
            log.warning("github fetch failed: %s", type(e).__name__)
            result = GithubStatus(
                status="error", message=f"GitHub 연결 실패 ({type(e).__name__})", repo=repo
            )
        _cache[key] = (time.monotonic(), result)
        return result


def clear_cache() -> None:
    _cache.clear()


def _client(api: str) -> httpx.Client:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"
    return httpx.Client(base_url=api, headers=headers, timeout=5.0, transport=_transport)


def _get(gh: httpx.Client, path: str, **params: Any) -> Any:
    r = gh.get(path, params=params)
    if r.status_code == 401:
        raise GithubError("인증 실패 — GITHUB_TOKEN을 확인하세요")
    if r.status_code == 403 and r.headers.get("x-ratelimit-remaining") == "0":
        raise GithubError("GitHub API 한도 초과 — GITHUB_TOKEN을 넣으면 한도가 늘어납니다")
    if r.status_code in (403, 404):
        hint = "" if settings.github_token else " (비공개 레포면 GITHUB_TOKEN 필요)"
        raise GithubError(f"레포에 접근할 수 없습니다 ({r.status_code}){hint}")
    r.raise_for_status()
    return r.json()


def _fetch(gh: httpx.Client, repo: str) -> GithubStatus:
    base = f"/repos/{repo}"
    issues = [
        GhIssue(
            number=i["number"],
            title=i["title"],
            assignees=[a["login"] for a in i.get("assignees") or []],
            labels=[lb["name"] for lb in i.get("labels") or []],
            url=i["html_url"],
        )
        for i in _get(gh, f"{base}/issues", state="open", per_page=50)
        if "pull_request" not in i  # issues API는 PR도 돌려준다
    ]
    pulls = [
        GhPull(
            number=p["number"],
            title=p["title"],
            author=p["user"]["login"],
            branch=p["head"]["ref"],
            draft=bool(p.get("draft")),
            checks=_checks(gh, base, p["head"]["sha"]),
            url=p["html_url"],
        )
        for p in _get(gh, f"{base}/pulls", state="open", per_page=MAX_PULLS)
    ]
    runs = [
        GhRun(
            name=r["name"],
            status=r["status"],
            conclusion=r.get("conclusion"),
            sha=r["head_sha"][:7],
            url=r["html_url"],
            created_at=r["created_at"],
        )
        for r in _get(gh, f"{base}/actions/runs", branch="main", per_page=5)["workflow_runs"]
    ]
    return GithubStatus(
        status="ok",
        repo=repo,
        fetched_at=datetime.now(UTC),
        issues=issues,
        pulls=pulls,
        main_runs=runs,
        claims=_claims(gh, base),
    )


def _checks(gh: httpx.Client, base: str, sha: str) -> Literal["pass", "fail", "pending", "none"]:
    runs = _get(gh, f"{base}/commits/{sha}/check-runs", per_page=50)["check_runs"]
    if not runs:
        return "none"
    if any(r["conclusion"] in ("failure", "timed_out", "action_required") for r in runs):
        return "fail"
    if any(r["status"] != "completed" for r in runs):
        return "pending"
    # success·skipped·neutral. 대체된(cancelled) 실행은 ship.sh처럼 실패로 보지 않는다
    return "pass"


def _claims(gh: httpx.Client, base: str) -> list[GhClaim]:
    """scripts/claim.sh의 claim/<번호> 브랜치. 커밋 메시지 = "<login> #<번호>"."""
    refs = _get(gh, f"{base}/git/matching-refs/heads/claim/")
    out = []
    for ref in refs[:MAX_CLAIMS]:
        n = ref["ref"].rsplit("/", 1)[-1]
        if not n.isdigit():
            continue
        msg = _get(gh, f"{base}/git/commits/{ref['object']['sha']}").get("message", "")
        out.append(GhClaim(issue=int(n), owner=msg.split(" ", 1)[0] or None))
    return out


def _git_origin() -> str:
    """네이티브 실행: git origin 주소 (docker는 GIT_REMOTE_URL로 받는다)."""
    try:
        out = subprocess.run(
            ["git", "-C", str(ROOT), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=2,
            check=True,
        )
        return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


# https://host/owner/name(.git) · git@host:owner/name(.git) · ssh://git@host(:port)/owner/name(.git)
_REMOTE = re.compile(
    r"^(?:https?://|ssh://)?(?:[^@/]+@)?([^/:]+)(?::\d+)?[:/]([^/]+/[^/]+?)(?:\.git)?/?$"
)


def _repo_from_remote(remote: str) -> str:
    m = _REMOTE.match(remote)
    return m[2] if m else ""


def _api_from_remote(remote: str) -> str:
    m = _REMOTE.match(remote)
    host = m[1] if m else "github.com"
    if host in ("github.com", "ssh.github.com"):
        return "https://api.github.com"
    return f"https://{host}/api/v3"  # GitHub Enterprise Server
