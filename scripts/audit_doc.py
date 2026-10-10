#!/usr/bin/env python3
"""make audit 결과를 docs/security-compliance.md 4절 '공통 점검' 표에 적는다 (문서가 없는 레포는 건너뜀).

    python3 scripts/audit_doc.py --secrets "<결과>" --deps "<결과>" [--stamp "<시각, SHA>"] [--doc docs/security-compliance.md]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEADER = ["점검", "방법", "결과"]
ROWS = {  # 표의 첫 칸 → (방법, 결과 접두)
    "비밀값이 저장소에 없음": "`make audit` — gitleaks detect (push 전 `make ship`·CI Security도 검사)",
    "의존성 취약점": "`make audit` — frontend `npm audit --omit=dev`, backend `pip-audit`",
}


def split_row(line: str) -> list[str]:
    return [c.strip() for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]


def update(text: str, secrets: str, deps: str, stamp: str) -> tuple[str, int]:
    """'공통 점검' 표의 두 행을 채운다 → (새 문서, 바뀐 행 수). 표가 없으면 0."""
    lines = text.splitlines()
    results = {"비밀값이 저장소에 없음": secrets, "의존성 취약점": deps}
    changed, i = 0, 0
    while i < len(lines):
        if lines[i].lstrip().startswith("|") and i + 1 < len(lines) and "---" in lines[i + 1] and split_row(lines[i]) == HEADER:
            j = i + 2
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                cells = split_row(lines[j])
                if cells and cells[0] in ROWS:
                    new = [cells[0], ROWS[cells[0]], f"{results[cells[0]]} ({stamp})".replace("|", "/")]
                    if cells[:3] != new:
                        lines[j] = "| " + " | ".join(new) + " |"
                        changed += 1
                j += 1
            i = j  # 같은 머리글의 표가 여러 개여도(3절 상세 등) 행 이름이 맞는 곳만 바꾼다
            continue
        i += 1
    return "\n".join(lines) + ("\n" if text.endswith("\n") else ""), changed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--secrets", required=True)
    ap.add_argument("--deps", required=True)
    ap.add_argument("--stamp", default="")
    ap.add_argument("--doc", default=str(ROOT / "docs" / "security-compliance.md"))
    args = ap.parse_args()
    doc = Path(args.doc)
    if not doc.exists():
        print("  docs/security-compliance.md 없음 — 결과는 위에만 (제출 문서가 없는 레포)")
        return 0
    text, n = update(doc.read_text(encoding="utf-8"), args.secrets, args.deps, args.stamp)
    if n:
        doc.write_text(text, encoding="utf-8")
        print(f"  security-compliance.md 4절 공통 점검 {n}행 갱신 — 커밋해서 근거로 남기세요")
    else:
        print("  security-compliance.md 4절: 바뀐 것 없음 (표가 없으면 양식 4절을 확인)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
