# docs/contracts/dashboard.md 와 1:1로 맞춘다. 변경 시 계약 문서 먼저 수정.
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.schemas.health import Health


class Migration(BaseModel):
    version: str
    applied_at: datetime


class Suite(BaseModel):
    name: str
    result: str


class TcResult(BaseModel):
    tc: str
    result: str
    test: str


class Tests(BaseModel):
    status: Literal["ok", "none"]
    run_id: str | None = None
    sha: str | None = None
    overall: Literal["PASS", "FAIL"] | None = None
    ran_at: str | None = None
    dirty: bool = False
    suites: list[Suite] = []
    tcs: list[TcResult] = []


class Req(BaseModel):
    id: str
    title: str
    priority: str
    issue: str
    state: str


class Reqs(BaseModel):
    status: Literal["ok", "none"]
    items: list[Req] = []


class Dashboard(BaseModel):
    generated_at: datetime
    server: Health
    migrations: list[Migration]
    tests: Tests
    reqs: Reqs


class GhIssue(BaseModel):
    number: int
    title: str
    assignees: list[str]
    labels: list[str]
    url: str


class GhPull(BaseModel):
    number: int
    title: str
    author: str
    branch: str
    draft: bool
    checks: Literal["pass", "fail", "pending", "none"]
    url: str


class GhRun(BaseModel):
    name: str
    status: str
    conclusion: str | None
    sha: str
    url: str
    created_at: datetime


class GhClaim(BaseModel):
    issue: int
    owner: str | None


class GithubStatus(BaseModel):
    status: Literal["ok", "unconfigured", "error"]
    message: str | None = None
    repo: str | None = None
    fetched_at: datetime | None = None
    issues: list[GhIssue] = []
    pulls: list[GhPull] = []
    main_runs: list[GhRun] = []
    claims: list[GhClaim] = []
