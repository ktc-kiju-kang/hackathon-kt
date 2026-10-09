"""현황판 API (docs/contracts/dashboard.md, #99)."""

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core import db
from app.core.config import settings
from app.main import app
from app.services import dashboard, dashboard_github, dashboard_leadtime

client = TestClient(app)
TOKEN = "ghp_secret_should_never_leak"

SUMMARY = """# 시험 실행 20261008-173723-b54b3d8

- 소스 SHA: `b54b3d891b4b1f0be69dc46065745235b6ff95e5`
- 전체: PASS
- 실행 시각: 2026-10-08 17:37 KST

| 묶음 | 결과 | 원본 |
|---|---|---|
| backend pytest | 61개 중 실패 0 | `backend.xml` |
| E2E | 3개 중 실패 0 | `e2e.xml` |

## TC별 결과

| TC | 결과 | 테스트 |
|---|---|---|
| TC-01-1 | PASS | test_tc_01_1_empty_title |
"""

PRD = """## 요구사항
| ID | 출처 | 요구사항 | 우선순위 | Issue | 상태 |
|---|---|---|---|---|---|
| REQ-01 | 주최 | 사용자는 할 일을 등록한다 | 필수 | #3 | 검증됨 |
| **REQ-02** | 팀 | 목록을 본다 | 선택 | #4 | 계획 |
"""


@pytest.fixture
def repo_root(tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard, "ROOT", tmp_path)
    return tmp_path


@pytest.fixture(autouse=True)
def _github_settings(monkeypatch):
    dashboard_github.clear_cache()
    dashboard_leadtime.clear_cache()
    monkeypatch.setattr(settings, "github_repo", "")
    monkeypatch.setattr(settings, "github_token", "")
    monkeypatch.setattr(settings, "github_api_url", "")
    monkeypatch.setattr(settings, "git_remote_url", "")
    monkeypatch.setattr(dashboard_github, "_git_origin", lambda: "")
    yield
    dashboard_github.clear_cache()
    dashboard_leadtime.clear_cache()


def test_dashboard_local_sections_empty_repo(repo_root):
    body = client.get("/api/dashboard").json()
    assert body["server"]["status"] == "ok" and body["server"]["db"] == "ok"
    # 테스트 schema에 적용된 마이그레이션 = 레포의 마이그레이션 파일 전부
    assert [m["version"] for m in body["migrations"]] == sorted(
        f.stem for f in db.MIGRATIONS_DIR.glob("*.sql")
    )
    assert body["tests"] == {
        "status": "none",
        "run_id": None,
        "sha": None,
        "overall": None,
        "ran_at": None,
        "dirty": False,
        "suites": [],
        "tcs": [],
    }
    assert body["reqs"] == {"status": "none", "items": []}


def test_read_reqs_index_with_child_links(tmp_path):
    """prd.md가 인덱스일 때: ID 칸이 하위 정의서 링크, 상태 앞에 '확인 조건' 칸."""
    prd = tmp_path / "prd.md"
    prd.write_text(
        "| ID | 출처 | 요구사항 | 우선순위 | Issue | 확인 조건 | 상태 |\n"
        "|---|---|---|---|---|---|---|\n"
        "| **[REQ-01](prd/REQ-01-todo.md)** | 주최 (SRC-01) | 할 일을 등록한다"
        " | 필수 | #3 | AC-01-1 | 구현됨-미검증 |\n",
        encoding="utf-8",
    )
    [r] = dashboard.read_reqs(prd).items
    assert (r.id, r.title, r.issue, r.state) == (
        "REQ-01",
        "할 일을 등록한다",
        "#3",
        "구현됨-미검증",
    )


def test_dashboard_reads_latest_evidence_and_prd(repo_root):
    old = repo_root / ".run" / "evidence" / "20261007-090000-aaaaaaa"
    new = repo_root / "docs" / "evidence" / "20261008-173723-b54b3d8"
    for d in (old, new):
        d.mkdir(parents=True)
    (old / "summary.md").write_text(SUMMARY.replace("PASS", "FAIL"), encoding="utf-8")
    (new / "summary.md").write_text(SUMMARY, encoding="utf-8")
    (repo_root / "docs" / "prd.md").write_text(PRD, encoding="utf-8")

    body = client.get("/api/dashboard").json()
    t = body["tests"]
    assert t["run_id"] == "20261008-173723-b54b3d8" and t["overall"] == "PASS"
    assert t["sha"].startswith("b54b3d8") and t["ran_at"] == "2026-10-08 17:37 KST"
    assert t["suites"][0] == {"name": "backend pytest", "result": "61개 중 실패 0"}
    assert t["tcs"] == [{"tc": "TC-01-1", "result": "PASS", "test": "test_tc_01_1_empty_title"}]
    assert [(r["id"], r["state"]) for r in body["reqs"]["items"]] == [
        ("REQ-01", "검증됨"),
        ("REQ-02", "계획"),
    ]


def test_dashboard_marks_dirty_run(repo_root):
    d = repo_root / ".run" / "evidence" / "20261008-120000-abcdef1-dirty"
    d.mkdir(parents=True)
    (d / "summary.md").write_text(SUMMARY, encoding="utf-8")
    assert client.get("/api/dashboard").json()["tests"]["dirty"] is True


def test_github_unconfigured_without_repo():
    body = client.get("/api/dashboard/github").json()
    assert body["status"] == "unconfigured" and "GITHUB_REPO" in body["message"]


def _fake_github(monkeypatch, handler):
    calls: list[str] = []

    def wrapped(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return handler(request)

    monkeypatch.setattr(dashboard_github, "_transport", httpx.MockTransport(wrapped))
    return calls


def _ok_handler(request: httpx.Request) -> httpx.Response:
    p = request.url.path
    assert request.headers["Authorization"] == f"Bearer {TOKEN}"
    if p.endswith("/issues"):
        return httpx.Response(
            200,
            json=[
                {"number": 7, "title": "할 일", "assignees": [{"login": "kim"}],
                 "labels": [{"name": "feature"}], "html_url": "u7"},
                {"number": 8, "title": "PR이 섞여 온다", "pull_request": {}, "html_url": "u8"},
            ],
        )  # fmt: skip
    if p.endswith("/pulls") and request.url.params.get("state") == "closed":
        merged = {"title": "머지됨", "user": {"login": "kim"}, "merged_at": "2026-10-08T07:00:00Z"}
        return httpx.Response(
            200,
            json=[{**merged, "number": 5}, {**merged, "number": 6, "merged_at": None}],
        )
    if p.endswith("/branches/main"):
        return httpx.Response(200, json={"commit": {"sha": "abcdef1234567890"}})
    if p.endswith("/pulls"):
        pr = {"title": "기능", "user": {"login": "lee"}, "draft": False}
        return httpx.Response(
            200,
            json=[
                {**pr, "number": 9, "head": {"ref": "feat/9-a", "sha": "s9"}, "html_url": "p9"},
                {**pr, "number": 10, "head": {"ref": "f/10", "sha": "s10"}, "html_url": "p10"},
            ],
        )
    if p.endswith("/commits/s9/check-runs"):
        runs = [{"status": "completed", "conclusion": "success"},
                {"status": "completed", "conclusion": "failure"}]  # fmt: skip
        return httpx.Response(200, json={"check_runs": runs})
    if p.endswith("/commits/s10/check-runs"):
        runs = [{"status": "completed", "conclusion": "success"},
                {"status": "completed", "conclusion": "cancelled"}]  # fmt: skip
        return httpx.Response(200, json={"check_runs": runs})
    if p.endswith("/actions/runs"):
        run = {"name": "CI", "status": "completed", "conclusion": "success"}
        run |= {"head_sha": "abcdef1234", "html_url": "r1", "created_at": "2026-10-08T08:00:00Z"}
        return httpx.Response(200, json={"workflow_runs": [run]})
    if p.endswith("/git/matching-refs/heads/claim/"):
        return httpx.Response(200, json=[{"ref": "refs/heads/claim/7", "object": {"sha": "c7"}}])
    if p.endswith("/git/commits/c7"):
        return httpx.Response(
            200, json={"message": "kim #7", "committer": {"date": "2026-10-07T01:00:00Z"}}
        )
    return httpx.Response(404)


def test_github_ok_and_token_never_in_response(monkeypatch):
    monkeypatch.setattr(settings, "github_repo", "team/app")
    monkeypatch.setattr(settings, "github_token", TOKEN)
    _fake_github(monkeypatch, _ok_handler)

    r = client.get("/api/dashboard/github")
    body = r.json()
    assert body["status"] == "ok" and body["repo"] == "team/app"
    assert [i["number"] for i in body["issues"]] == [7]  # PR은 Issue 목록에서 뺀다
    assert {p["number"]: p["checks"] for p in body["pulls"]} == {9: "fail", 10: "pass"}
    assert body["main_runs"][0]["sha"] == "abcdef1"
    assert body["claims"] == [{"issue": 7, "owner": "kim", "claimed_at": "2026-10-07T01:00:00Z"}]
    assert body["main_sha"] == "abcdef1234567890"
    assert [(m["number"], m["author"]) for m in body["recent_merges"]] == [
        (5, "kim")
    ]  # 닫히기만 한 PR 제외
    assert TOKEN not in r.text


def test_github_auth_failure_is_shown_without_token(monkeypatch):
    monkeypatch.setattr(settings, "github_repo", "team/app")
    monkeypatch.setattr(settings, "github_token", TOKEN)
    _fake_github(monkeypatch, lambda req: httpx.Response(401, json={"message": "Bad credentials"}))

    r = client.get("/api/dashboard/github")
    assert r.status_code == 200
    assert r.json()["status"] == "error" and "인증 실패" in r.json()["message"]
    assert TOKEN not in r.text


def test_github_network_failure_does_not_break_dashboard(monkeypatch, repo_root):
    monkeypatch.setattr(settings, "github_repo", "team/app")

    def boom(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    _fake_github(monkeypatch, boom)
    assert client.get("/api/dashboard/github").json()["status"] == "error"
    assert client.get("/api/dashboard").status_code == 200  # 로컬 칸은 그대로


def test_github_is_cached(monkeypatch):
    monkeypatch.setattr(settings, "github_repo", "team/app")
    monkeypatch.setattr(settings, "github_token", TOKEN)
    calls = _fake_github(monkeypatch, _ok_handler)
    client.get("/api/dashboard/github")
    n = len(calls)
    client.get("/api/dashboard/github")
    assert len(calls) == n  # 60초 안에는 GitHub을 다시 부르지 않는다


@pytest.mark.parametrize(
    ("remote", "repo", "api"),
    [
        ("https://github.com/team/app.git", "team/app", "https://api.github.com"),
        ("git@github.com:team/app.git", "team/app", "https://api.github.com"),
        ("ssh://ssh.github.com:443/team/app.git", "team/app", "https://api.github.com"),
        ("https://ghe.corp.example/team/app", "team/app", "https://ghe.corp.example/api/v3"),
        ("", "", "https://api.github.com"),
    ],
)
def test_repo_and_api_from_remote(remote, repo, api):
    assert dashboard_github._repo_from_remote(remote) == repo
    assert dashboard_github._api_from_remote(remote) == api


@pytest.mark.parametrize(
    ("reply", "expect"),
    [
        (httpx.Response(403, headers={"x-ratelimit-remaining": "0"}), "한도 초과"),
        (httpx.Response(404), "GITHUB_TOKEN 필요"),  # 토큰 없이 비공개 레포
        (httpx.Response(200, text="<html>login</html>"), "응답 형식 오류"),  # GHE 로그인 페이지
        (httpx.Response(200, json={"unexpected": 1}), "응답 형식 오류"),
    ],
)
def test_github_failures_become_error_status(monkeypatch, reply, expect):
    monkeypatch.setattr(settings, "github_repo", "team/app")
    _fake_github(monkeypatch, lambda req: reply)
    r = client.get("/api/dashboard/github")
    assert r.status_code == 200
    assert r.json()["status"] == "error" and expect in r.json()["message"]


def test_token_not_sent_to_non_github_origin(monkeypatch):
    """origin이 GitHub이 아닌 호스트면(미러 등) GITHUB_API_URL 없이 토큰을 보내지 않는다."""
    monkeypatch.setattr(settings, "git_remote_url", "https://mirror.example/team/app.git")
    monkeypatch.setattr(settings, "github_token", TOKEN)
    seen: list[str | None] = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req.headers.get("Authorization"))
        return httpx.Response(401)

    _fake_github(monkeypatch, handler)
    client.get("/api/dashboard/github")
    assert seen and all(h is None for h in seen)


def test_bad_repo_name_is_unconfigured(monkeypatch):
    monkeypatch.setattr(settings, "github_repo", "team/../../admin?x=1")
    assert client.get("/api/dashboard/github").json()["status"] == "unconfigured"


def _evidence(root, run_id: str, overall: str, sha: str, suites: str) -> None:
    d = root / "docs" / "evidence" / run_id
    d.mkdir(parents=True)
    (d / "summary.md").write_text(
        f"- 소스 SHA: `{sha}`\n- 전체: {overall}\n\n"
        f"| 묶음 | 결과 | 원본 |\n|---|---|---|\n{suites}",
        encoding="utf-8",
    )


def test_history_counts_runs_in_order(repo_root):
    _evidence(
        repo_root, "20261008-090000-aaaaaaa", "FAIL", "a" * 40, "| be | 10개 중 실패 2 | x |\n"
    )
    _evidence(
        repo_root,
        "20261008-100000-bbbbbbb",
        "PASS",
        "b" * 40,
        "| be | 10개 중 실패 0 | x |\n| e2e | 3개 중 실패 0 | x |\n",
    )
    h = client.get("/api/dashboard").json()["test_history"]
    assert [(r["run_id"][:15], r["total"], r["failed"], r["overall"]) for r in h] == [
        ("20261008-090000", 10, 2, "FAIL"),
        ("20261008-100000", 13, 0, "PASS"),
    ]
    assert h[0]["ran_at"].startswith("2026-10-08T09:00:00+09:00")


def _checks(body):
    return {c["key"]: c["status"] for c in body["readiness"]["checks"]}


def test_readiness_not_applicable_without_submission_docs(repo_root):
    body = client.get("/api/dashboard").json()
    assert body["readiness"]["deadline"].startswith("2026-10-15T00:00:00+09:00")
    assert _checks(body) | {"committed": "x"} == {
        "committed": "x",  # 테스트 환경의 git 상태에 따라 다르다
        "evidence": "na",
        "placeholders": "na",
        "reqs": "na",
    }


def test_readiness_checks_team_repo(repo_root, monkeypatch):
    sha = "c" * 40
    monkeypatch.setattr(settings, "app_version", sha)
    (repo_root / "docs").mkdir()
    (repo_root / "docs" / "prd.md").write_text(PRD, encoding="utf-8")  # REQ-02가 계획
    (repo_root / "README.md").write_text("# {{서비스 이름}}\n{{설명}}\n", encoding="utf-8")
    (repo_root / "docs" / "prd").mkdir()
    (repo_root / "docs" / "prd" / "REQ-01-a.md").write_text("{{AC}}", encoding="utf-8")
    (repo_root / "docs" / "prd" / "_memo.md").write_text("{{메모}}", encoding="utf-8")  # 제외
    _evidence(repo_root, "20261008-100000-ccccccc", "PASS", sha, "| be | 10개 중 실패 0 | x |\n")
    body = client.get("/api/dashboard").json()
    assert _checks(body) == {
        "committed": "ok",
        "evidence": "ok",
        "placeholders": "fail",
        "reqs": "fail",
    }
    detail = {c["key"]: c["detail"] for c in body["readiness"]["checks"]}
    assert (
        detail["placeholders"] == "README.md 2개 · docs/prd/REQ-01-a.md 1개"
        and "REQ-02" in detail["reqs"]
    )


def test_readiness_evidence_from_other_commit_or_dirty_fails(repo_root, monkeypatch):
    monkeypatch.setattr(settings, "app_version", "d" * 40 + "-dirty")
    (repo_root / "docs").mkdir()
    (repo_root / "docs" / "prd.md").write_text(PRD, encoding="utf-8")
    _evidence(
        repo_root, "20261008-100000-eeeeeee", "PASS", "e" * 40, "| be | 1개 중 실패 0 | x |\n"
    )
    c = _checks(client.get("/api/dashboard").json())
    assert c["committed"] == "fail" and c["evidence"] == "fail"


# ── 리드타임 (#107) ──────────────────────────────────────────────────────────

H = 3600


def _leadtime_handler(prs: list[dict], issues: list[dict]):
    """Issue 목록(created_at)과 닫힌 PR 목록(merged_at)만 돌려주는 가짜 GitHub."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == f"Bearer {TOKEN}"
        p = request.url.path
        if p.endswith("/pulls") and request.url.params.get("state") == "closed":
            return httpx.Response(200, json=prs)
        if p.endswith("/issues") and request.url.params.get("state") == "closed":
            return httpx.Response(200, json=issues)
        return httpx.Response(404)

    return handler


def _issue(number: int, created: str) -> dict:
    return {"number": number, "title": f"이슈 {number}", "created_at": created}


def _pr(number: int, merged: str | None, body: str | None = None, ref: str = "x") -> dict:
    return {"number": number, "merged_at": merged, "body": body, "head": {"ref": ref}}


def _configure(monkeypatch):
    monkeypatch.setattr(settings, "github_repo", "team/app")
    monkeypatch.setattr(settings, "github_token", TOKEN)


def test_tc_lt_01_median_and_buckets(monkeypatch):
    """TC-LT-01: 머지된 PR만 집계 — Issue를 PR 본문(Closes) 또는 브랜치 이름으로 찾는다."""
    _configure(monkeypatch)
    issues = [
        _issue(7, "2026-10-08T00:00:00Z"),
        _issue(8, "2026-10-08T00:00:00Z"),
        _issue(9, "2026-10-08T00:00:00Z"),
        {**_issue(10, "2026-10-08T00:00:00Z"), "pull_request": {}},  # PR이 섞여 온다
    ]
    prs = [
        _pr(20, "2026-10-08T02:00:00Z", body="기능 추가\n\nCloses #7"),  # 2시간
        _pr(21, "2026-10-09T06:00:00Z", ref="feat/8-big-one"),  # 30시간 (브랜치로 찾음)
        _pr(22, None, body="Closes #9"),  # 머지 없이 닫힘 → 뺀다
        _pr(23, "2026-10-08T01:00:00Z", body="이슈 언급 없음"),  # Issue를 못 찾음 → 뺀다
        _pr(24, "2026-10-08T01:00:00Z", body="Closes #999"),  # 목록 밖 Issue → 뺀다
        _pr(25, "2026-10-08T09:00:00Z", body="Closes #10"),  # #10은 PR이라 Issue가 아님 → 뺀다
    ]
    _fake_github(monkeypatch, _leadtime_handler(prs, issues))
    r = client.get("/api/dashboard/leadtime")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["repo"] == "team/app" and body["fetched_at"]
    assert body["count"] == 2
    assert body["median_seconds"] == (2 * H + 30 * H) // 2  # 짝수 개면 가운데 두 값의 평균
    counts = {b["label"]: b["count"] for b in body["buckets"]}
    assert counts == {"1시간 미만": 0, "1~4시간": 1, "4~24시간": 0, "1~3일": 1, "3일 이상": 0}
    assert [b["label"] for b in body["buckets"]][0] == "1시간 미만"  # 순서 고정
    assert body["buckets"][-1]["max_seconds"] is None
    assert TOKEN not in r.text and r.headers["cache-control"] == "no-store"


def test_tc_lt_02_no_merged_prs_is_empty_not_error(monkeypatch):
    """TC-LT-02: 머지된 PR이 없으면 오류가 아니라 빈 상태 (건수 0, 중앙값 null)."""
    _configure(monkeypatch)
    _fake_github(monkeypatch, _leadtime_handler([_pr(1, None, body="Closes #1")], []))
    body = client.get("/api/dashboard/leadtime").json()
    assert body["status"] == "ok" and body["message"] is None
    assert body["count"] == 0 and body["median_seconds"] is None
    assert len(body["buckets"]) == 5 and all(b["count"] == 0 for b in body["buckets"])


def test_tc_lt_03_github_failure_is_isolated_to_leadtime(monkeypatch, repo_root):
    """TC-LT-03: GitHub 조회가 실패해도 리드타임 칸만 오류 — 기존 현황판 응답은 그대로."""
    _configure(monkeypatch)
    _fake_github(monkeypatch, lambda req: httpx.Response(401, json={"message": "Bad credentials"}))
    r = client.get("/api/dashboard/leadtime")
    assert r.status_code == 200  # 오류도 200 — 화면이 그 칸만 오류로 보여 준다
    body = r.json()
    assert body["status"] == "error" and "인증 실패" in body["message"]
    assert body["count"] == 0 and body["median_seconds"] is None and body["buckets"] == []
    assert TOKEN not in r.text
    assert client.get("/api/dashboard").status_code == 200  # 로컬 칸은 GitHub과 무관


def test_tc_lt_04_network_failure_becomes_error_status(monkeypatch):
    """TC-LT-04: 연결 실패·응답 형식 오류도 error로 바꾼다 (500이 되지 않는다)."""
    _configure(monkeypatch)

    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    _fake_github(monkeypatch, boom)
    body = client.get("/api/dashboard/leadtime").json()
    assert body["status"] == "error" and "연결 실패" in body["message"]

    dashboard_leadtime.clear_cache()
    _fake_github(monkeypatch, lambda req: httpx.Response(200, text="<html>login</html>"))
    body = client.get("/api/dashboard/leadtime").json()
    assert body["status"] == "error" and "형식 오류" in body["message"]


def test_tc_lt_05_unconfigured_without_repo():
    """TC-LT-05: 레포를 모르면 unconfigured (GitHub 칸과 같은 안내)."""
    body = client.get("/api/dashboard/leadtime").json()
    assert body["status"] == "unconfigured" and "GITHUB_REPO" in body["message"]
    assert body["buckets"] == []


def test_tc_lt_06_leadtime_is_cached(monkeypatch):
    """TC-LT-06: 60초 캐시 — 화면을 여러 번 새로 고쳐도 GitHub을 다시 부르지 않는다."""
    _configure(monkeypatch)
    calls = _fake_github(monkeypatch, _leadtime_handler([], []))
    client.get("/api/dashboard/leadtime")
    assert len(calls) == 2  # 닫힌 PR 1번 + 닫힌 Issue 1번
    client.get("/api/dashboard/leadtime")
    assert len(calls) == 2


def test_tc_lt_07_merge_before_issue_clamps_to_zero(monkeypatch):
    """TC-LT-07: 시계가 어긋나 머지가 Issue보다 이르면 음수 대신 0초로 센다."""
    _configure(monkeypatch)
    issues = [_issue(3, "2026-10-08T05:00:00Z")]
    prs = [_pr(30, "2026-10-08T04:00:00Z", body="Fixes #3")]
    _fake_github(monkeypatch, _leadtime_handler(prs, issues))
    body = client.get("/api/dashboard/leadtime").json()
    assert body["count"] == 1 and body["median_seconds"] == 0
    assert body["buckets"][0]["count"] == 1


@pytest.mark.parametrize(
    ("pr", "expect"),
    [
        ({"body": "Closes #12", "head": {"ref": "feat/9-x"}}, 12),  # 본문이 브랜치보다 먼저
        ({"body": "closes: #12", "head": {"ref": ""}}, 12),
        ({"body": "Resolved #4 와 fixes #5", "head": {"ref": ""}}, 4),
        ({"body": None, "head": {"ref": "fix/33-bug"}}, 33),
        ({"body": "참고 #8", "head": {"ref": "chore/deps"}}, None),
        ({"head": {}}, None),
    ],
)
def test_tc_lt_08_issue_number_from_pr(pr, expect):
    """TC-LT-08: PR → Issue 번호 (Closes/Fixes/Resolves, 없으면 브랜치 이름)."""
    assert dashboard_leadtime._issue_number(pr) == expect
