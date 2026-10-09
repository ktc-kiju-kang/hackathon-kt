"""새 마이그레이션이 계약의 테이블 SQL 초안 그대로인지 대조한다 (역할 분담의 BE 루프 예외, docs/requirements-flow.md).

    python3 scripts/migration_draft.py [--base origin/main]

base...HEAD에서 추가된 `database/migrations/*.sql`의 문장마다, base의 `docs/contracts/*.md`(README 제외)의
`## 테이블` 절 SQL 초안에 같은 문장이 있는지 본다. 비교는 주석·대소문자·공백을 빼고 한다.
기존 마이그레이션을 고치거나 지웠거나, CREATE TABLE·CREATE INDEX 말고 다른 문장이 있으면 그것도 이유로 적는다.
출력: 이유 한 줄씩. 종료코드 0=초안 그대로(또는 새 마이그레이션 없음), 1=다름, 2=오류. make ship(lib.sh migration_gate)이 쓴다.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALLOWED = re.compile(r"^create (unique )?(table|index) ")


def normalize(sql: str) -> list[str]:
    """주석을 빼고 소문자·공백 하나로 맞춘 문장 목록 (괄호·쉼표 앞뒤 공백도 없앤다)."""
    sql = re.sub(r"--[^\n]*", "", sql).lower()
    out = []
    for stmt in sql.split(";"):
        s = re.sub(r"\s+", " ", stmt).strip()
        s = re.sub(r"\s*([(),])\s*", r"\1", s)
        if s:
            out.append(s)
    return out


def draft_sql(contract: str) -> str:
    """계약의 `## 테이블` 절에서 SQL만 — 4칸 들여쓴 줄과 ``` 코드 블록 안의 줄."""
    m = re.search(r"^## 테이블[^\n]*\n(.*?)(?=^## |\Z)", contract, re.M | re.S)
    if not m:
        return ""
    lines, fenced = [], False
    for line in m.group(1).splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if fenced or line.startswith(("    ", "\t")):
            lines.append(line)
    return "\n".join(lines)


def check(base: str, root: Path = ROOT) -> list[str]:
    def git(*args: str) -> str:
        return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=True).stdout

    # 초안은 base(머지된 계약 = 사람이 G3에서 본 것)에서 읽는다 — 같은 PR에서 초안과 마이그레이션을 함께 바꿔도 통과하지 않게
    reasons, drafts = [], set()
    for f in git("ls-tree", "--name-only", base, "docs/contracts/").split():
        if f.endswith(".md") and not f.endswith("/README.md"):
            drafts.update(normalize(draft_sql(git("show", f"{base}:{f}"))))
    for row in git("diff", "--name-status", f"{base}...HEAD", "--", "database/migrations/").splitlines():
        status, path = row.split("\t")[0], row.split("\t")[-1]
        if not status.startswith("A"):
            reasons.append(f"{path}: 기존 마이그레이션을 고치거나 지움 ({status}) — 사람 확인")
            continue
        for stmt in normalize((root / path).read_text(encoding="utf-8")):
            short = stmt[:80]
            if not ALLOWED.match(stmt):
                reasons.append(f"{path}: CREATE TABLE·INDEX가 아닌 문장 — {short}")
            elif stmt not in drafts:
                reasons.append(f"{path}: 계약의 테이블 SQL 초안에 없는 문장 — {short}")
    return reasons


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="origin/main")
    args = ap.parse_args()
    try:
        reasons = check(args.base)
    except (subprocess.CalledProcessError, OSError, UnicodeDecodeError) as e:
        print(f"대조 실패: {e}", file=sys.stderr)  # lib.sh migration_gate가 이 줄을 그대로 보인다
        return 2
    for r in reasons:
        print(r)
    return 1 if reasons else 0


if __name__ == "__main__":
    sys.exit(main())
