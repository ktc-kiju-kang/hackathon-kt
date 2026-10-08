"""현황판 API (docs/contracts/dashboard.md, #99)."""

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services import dashboard, dashboard_github

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
    monkeypatch.setattr(settings, "github_repo", "")
    monkeypatch.setattr(settings, "github_token", "")
    monkeypatch.setattr(settings, "github_api_url", "")
    monkeypatch.setattr(settings, "git_remote_url", "")
    monkeypatch.setattr(dashboard_github, "_git_origin", lambda: "")
    yield
    dashboard_github.clear_cache()


def test_dashboard_local_sections_empty_repo(repo_root):
    body = client.get("/api/dashboard").json()
    assert body["server"]["status"] == "ok" and body["server"]["db"] == "ok"
    assert [m["version"] for m in body["migrations"]] == ["0001_chat"]  # 테스트 schema에 적용됨
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
        return httpx.Response(200, json={"message": "kim #7"})
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
    assert body["claims"] == [{"issue": 7, "owner": "kim"}]
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
