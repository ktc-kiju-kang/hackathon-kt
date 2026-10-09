"""현황판 로컬 칸: 서버·DB·시험 근거·REQ 진행 (docs/contracts/dashboard.md). 외부 호출 없음."""

import logging
import re
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

from app.core.config import settings
from app.core.db import get_db
from app.schemas.dashboard import (
    Check,
    Dashboard,
    Migration,
    Readiness,
    Req,
    Reqs,
    Suite,
    TcResult,
    TestRun,
    Tests,
)
from app.services.health import get_health

log = logging.getLogger(__name__)

# 레포 루트 (네이티브: 체크아웃 폴더, docker: /app)
# docker에서는 compose.yaml이 docs·.run/evidence를 읽기 전용으로 붙인다
ROOT = Path(__file__).resolve().parents[3]
_RUN_ID = re.compile(r"\d{8}-\d{6}-[0-9a-f]{7}(-dirty)?")
_SUITE = re.compile(r"(\d+)개 중 실패 (\d+)")
KST = timezone(timedelta(hours=9))
HISTORY_MAX = 20
# 제출 문서 (templates/submission, scripts/check-docs.py와 같은 목록)
SUBMISSION_DOCS = [
    "README.md",
    *(
        f"docs/{n}.md"
        for n in (
            "project-brief",
            "prd",
            "arch",
            "experience",
            "development",
            "security-compliance",
            "e2e-test",
        )
    ),
]


def get_dashboard() -> Dashboard:
    server = get_health()
    tests = latest_tests(ROOT)
    reqs = read_reqs(ROOT / "docs" / "prd.md")
    return Dashboard(
        generated_at=datetime.now(UTC),
        server=server,
        migrations=_migrations(),
        tests=tests,
        reqs=reqs,
        test_history=test_history(ROOT),
        readiness=readiness(ROOT, server.version, reqs),
    )


def _migrations() -> list[Migration]:
    try:
        with get_db() as db:
            rows = db.execute(
                "select version, applied_at from schema_migrations order by version"
            ).fetchall()
        return [Migration(**r) for r in rows]
    except Exception as e:  # DB 장애는 서버 칸의 db 상태로 보인다 — 현황판 자체는 200
        log.warning("dashboard migrations failed: %s", e)
        return []


def _table_rows(text: str, first_header: str) -> list[list[str]]:
    """첫 칸 제목이 first_header인 markdown 표의 본문 행들."""
    lines, out, i = text.splitlines(), [], 0
    while i < len(lines):
        cells = _cells(lines[i])
        if cells[:1] == [first_header] and i + 1 < len(lines) and "---" in lines[i + 1]:
            j = i + 2
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                out.append(_cells(lines[j]))
                j += 1
            i = j
        else:
            i += 1
    return out


def _cells(line: str) -> list[str]:
    if not line.lstrip().startswith("|"):
        return []
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _runs(root: Path, only_docs: bool = False) -> list[Path]:
    """make e2e 근거 폴더들 (docs/evidence·.run/evidence의 <실행>/summary.md), 오래된 것부터."""
    bases = [root / "docs" / "evidence"] + ([] if only_docs else [root / ".run" / "evidence"])
    runs = [
        p
        for base in bases
        if base.is_dir()
        for p in base.iterdir()
        if _RUN_ID.fullmatch(p.name) and (p / "summary.md").is_file()
    ]
    return sorted(runs, key=lambda p: p.name)  # 이름이 시각으로 시작한다


def _field(text: str, name: str) -> str | None:
    m = re.search(rf"^- {name}: (.+)$", text, re.M)
    return m[1].strip().strip("`") if m else None


def _overall(text: str) -> Literal["PASS", "FAIL"] | None:
    v = _field(text, "전체")
    return "PASS" if v == "PASS" else "FAIL" if v == "FAIL" else None


def latest_tests(root: Path) -> Tests:
    """가장 최근 make e2e 근거."""
    runs = _runs(root)
    if not runs:
        return Tests(status="none")
    run = runs[-1]
    text = (run / "summary.md").read_text(encoding="utf-8", errors="replace")

    def field(name: str) -> str | None:
        return _field(text, name)

    overall = field("전체")
    return Tests(
        status="ok",
        run_id=run.name,
        sha=field("소스 SHA"),
        overall=overall if overall in ("PASS", "FAIL") else None,
        ran_at=field("실행 시각"),
        dirty=run.name.endswith("-dirty"),
        suites=[Suite(name=c[0], result=c[1]) for c in _table_rows(text, "묶음") if len(c) >= 2],
        tcs=[
            TcResult(tc=c[0], result=c[1], test=c[2])
            for c in _table_rows(text, "TC")
            if len(c) >= 3
        ],
    )


def read_reqs(prd: Path) -> Reqs:
    """docs/prd.md 요구사항 표: | ID | 출처 | 요구사항 | 우선순위 | Issue | (확인 조건) | 상태 |.

    ID 칸은 하위 정의서 링크일 수 있다: [REQ-01](prd/REQ-01-login.md).
    """
    if not prd.is_file():
        return Reqs(status="none")
    items = []
    for c in _table_rows(prd.read_text(encoding="utf-8", errors="replace"), "ID"):
        rid = re.sub(r"[*`\[\]]|\(.*?\)$", "", c[0]).strip()
        if re.fullmatch(r"REQ-\d+", rid) and len(c) >= 6:
            items.append(Req(id=rid, title=c[2], priority=c[3], issue=c[4], state=c[-1]))
    return Reqs(status="ok", items=items)


def test_history(root: Path) -> list[TestRun]:
    """최근 실행 20개의 통과·실패 수 (추이 차트용)."""
    out = []
    for run in _runs(root)[-HISTORY_MAX:]:
        text = (run / "summary.md").read_text(encoding="utf-8", errors="replace")
        counts = [(int(a), int(b)) for a, b in _SUITE.findall(text)]
        out.append(
            TestRun(
                run_id=run.name,
                sha=_field(text, "소스 SHA"),
                ran_at=datetime.strptime(run.name[:15], "%Y%m%d-%H%M%S").replace(tzinfo=KST),
                overall=_overall(text),
                total=sum(t for t, _ in counts),
                failed=sum(f for _, f in counts),
                dirty=run.name.endswith("-dirty"),
            )
        )
    return out


def readiness(root: Path, version: str | None, reqs: Reqs) -> Readiness:
    """제출 준비도 — scripts/submit-check.sh와 같은 기준 중 서버가 볼 수 있는 것."""
    has_docs = (root / "docs" / "prd.md").is_file()
    na = "제출 문서가 없는 레포 (키트 원본)"
    checks = []

    dirty = bool(version and version.endswith("-dirty"))
    checks.append(
        Check(
            key="committed",
            label="커밋 안 된 변경 없음",
            status="na" if not version else "fail" if dirty else "ok",
            detail="실행 버전을 모름"
            if not version
            else "커밋 안 된 코드 변경이 있음 — 커밋 후 make serve"
            if dirty
            else f"실행 버전 {version[:7]}",
        )
    )

    if not has_docs:
        checks.append(
            Check(key="evidence", label="이 커밋의 시험 근거 PASS", status="na", detail=na)
        )
    else:
        clean = [r for r in _runs(root, only_docs=True) if not r.name.endswith("-dirty")]
        last = clean[-1] if clean else None
        text = (last / "summary.md").read_text(encoding="utf-8", errors="replace") if last else ""
        sha = _field(text, "소스 SHA") or ""
        same = bool(version and sha and sha[:7] == version.replace("-dirty", "")[:7])
        ok = bool(last) and same and _overall(text) == "PASS"
        detail = (
            "docs/evidence/에 근거 없음 → make e2e 후 커밋 (main은 make record)"
            if not last
            else f"최신 근거 {last.name}: "
            + ("전체 PASS" if _overall(text) == "PASS" else "PASS 아님")
            + ("" if same else f" · 실행 버전과 다른 커밋({sha[:7]})")
        )
        checks.append(
            Check(
                key="evidence",
                label="이 커밋의 시험 근거 PASS",
                status="ok" if ok else "fail",
                detail=detail,
            )
        )

    if not has_docs:
        checks.append(Check(key="placeholders", label="문서 자리표시 0개", status="na", detail=na))
    else:
        left = {}
        for rel in SUBMISSION_DOCS:
            f = root / rel
            if f.is_file():
                n = len(
                    re.findall(r"\{\{[^}]*\}\}", f.read_text(encoding="utf-8", errors="replace"))
                )
                if n:
                    left[rel] = n
        checks.append(
            Check(
                key="placeholders",
                label="문서 자리표시 0개",
                status="fail" if left else "ok",
                detail=" · ".join(f"{k} {v}개" for k, v in left.items()) or "남은 {{…}} 없음",
            )
        )

    counted = [i for i in reqs.items if not i.state.startswith("제외")]
    left_reqs = [i.id for i in counted if i.state != "검증됨"]
    checks.append(
        Check(
            key="reqs",
            label="REQ 전부 검증됨",
            status="na" if reqs.status == "none" or not counted else "fail" if left_reqs else "ok",
            detail=na
            if reqs.status == "none"
            else "REQ 없음"
            if not counted
            else "미검증 " + ", ".join(left_reqs)
            if left_reqs
            else f"{len(counted)}개 모두 검증됨",
        )
    )
    return Readiness(deadline=datetime.fromisoformat(settings.submit_deadline), checks=checks)
