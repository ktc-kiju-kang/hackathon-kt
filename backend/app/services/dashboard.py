"""현황판 로컬 칸: 서버·DB·시험 근거·REQ 진행 (docs/contracts/dashboard.md). 외부 호출 없음."""

import logging
import re
from datetime import UTC, datetime
from pathlib import Path

from app.core.db import get_db
from app.schemas.dashboard import Dashboard, Migration, Req, Reqs, Suite, TcResult, Tests
from app.services.health import get_health

log = logging.getLogger(__name__)

# 레포 루트 (네이티브: 체크아웃 폴더, docker: /app)
# docker에서는 compose.yaml이 docs·.run/evidence를 읽기 전용으로 붙인다
ROOT = Path(__file__).resolve().parents[3]
_RUN_ID = re.compile(r"\d{8}-\d{6}-[0-9a-f]{7}(-dirty)?")


def get_dashboard() -> Dashboard:
    return Dashboard(
        generated_at=datetime.now(UTC),
        server=get_health(),
        migrations=_migrations(),
        tests=latest_tests(ROOT),
        reqs=read_reqs(ROOT / "docs" / "prd.md"),
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


def latest_tests(root: Path) -> Tests:
    """가장 최근 make e2e 근거 (docs/evidence 또는 .run/evidence의 <실행>/summary.md)."""
    runs = [
        p
        for base in (root / "docs" / "evidence", root / ".run" / "evidence")
        if base.is_dir()
        for p in base.iterdir()
        if _RUN_ID.fullmatch(p.name) and (p / "summary.md").is_file()
    ]
    if not runs:
        return Tests(status="none")
    run = max(runs, key=lambda p: p.name)  # 이름이 시각으로 시작한다
    text = (run / "summary.md").read_text(encoding="utf-8", errors="replace")

    def field(name: str) -> str | None:
        m = re.search(rf"^- {name}: (.+)$", text, re.M)
        return m[1].strip().strip("`") if m else None

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
    """docs/prd.md 요구사항 표: | ID | 출처 | 요구사항 | 우선순위 | Issue | 상태 |."""
    if not prd.is_file():
        return Reqs(status="none")
    items = []
    for c in _table_rows(prd.read_text(encoding="utf-8", errors="replace"), "ID"):
        rid = re.sub(r"[*`\[\]]", "", c[0]).strip()
        if re.fullmatch(r"REQ-\d+", rid) and len(c) >= 6:
            items.append(Req(id=rid, title=c[2], priority=c[3], issue=c[4], state=c[-1]))
    return Reqs(status="ok", items=items)
