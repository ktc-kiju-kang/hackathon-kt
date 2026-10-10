#!/usr/bin/env python3
"""README '결과 한눈에' 표와 security-compliance.md 1절 요약을 문서의 실제 표에서 세어 채운다.

    python3 scripts/readme_summary.py [--root .] [--dry-run]

세는 곳: prd.md 요구사항 표(상태·출처), e2e-test.md 시험 목록(상태), security-compliance.md 2절(상태), GitHub Issue(완료/전체 — gh가 되면).
make record가 부른다 (손으로 적은 숫자가 표와 어긋나지 않게). scripts/check-docs.py가 어긋남을 잡는다 (--draft는 경고, 제출 전 strict는 오류).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README_HEADER = ["항목", "값", "근거"]


def split_row(line: str) -> list[str]:
    return [c.strip() for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]


def tables(text: str) -> list[tuple[int, list[str], list[tuple[int, list[str]]]]]:
    """(헤더 줄 번호, 헤더, [(줄 번호, 칸들)…])"""
    out, lines, i = [], text.splitlines(), 0
    while i < len(lines):
        if lines[i].lstrip().startswith("|") and i + 1 < len(lines) and "---" in lines[i + 1]:
            header, rows, j = split_row(lines[i]), [], i + 2
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                rows.append((j, split_row(lines[j])))
                j += 1
            out.append((i, header, rows))
            i = j
        else:
            i += 1
    return out


def plain(cell: str) -> str:
    """**[REQ-01](prd/…)** → REQ-01"""
    return re.sub(r"\(.*?\)$", "", re.sub(r"[*`\[\]]", "", cell)).strip()


def count_reqs(prd: str) -> dict[str, int]:
    c = {"verified": 0, "total": 0, "host": 0, "team": 0}
    for _, header, rows in tables(prd):
        if header[:1] != ["ID"] or "상태" not in header or "출처" not in header:
            continue
        for _, cells in rows:
            if len(cells) < len(header) or not re.fullmatch(r"REQ-\d+", plain(cells[0])):
                continue
            c["total"] += 1
            if cells[header.index("상태")].startswith("검증됨"):
                c["verified"] += 1
            src = cells[header.index("출처")]
            if src.startswith("주최"):
                c["host"] += 1
            elif src.startswith("팀"):
                c["team"] += 1
    return c


def count_tcs(e2e: str) -> dict[str, int]:
    c = {"PASS": 0, "FAIL": 0, "SKIP": 0, "미실행": 0}
    for _, header, rows in tables(e2e):
        if header[:1] != ["TC"] or "확인 조건" not in header or "상태" not in header:
            continue
        for _, cells in rows:
            if len(cells) < len(header):
                continue
            st = cells[header.index("상태")]
            for k in c:
                if st.startswith(k):
                    c[k] += 1
    return c


SEC_STATES = ["적용-검증됨", "적용-미검증", "해당 없음", "예외"]


def count_secs(comp: str) -> dict[str, int]:
    c = dict.fromkeys(SEC_STATES, 0)
    for _, header, rows in tables(comp):
        if header[:1] != ["SEC"] or "상태" not in header:
            continue
        for _, cells in rows:
            if len(cells) < len(header) or not re.fullmatch(r"SEC-\d+", plain(cells[0])):
                continue
            st = cells[header.index("상태")]
            for k in SEC_STATES:
                if st.startswith(k):
                    c[k] += 1
                    break
    return c


def count_issues() -> tuple[int, int, str] | None:
    """(완료로 닫힌 Issue, 전체 — not planned 제외, Issues URL). gh가 안 되면 None."""
    try:
        out = subprocess.run(
            ["gh", "issue", "list", "--state", "all", "--limit", "500", "--json", "state,stateReason,url"],
            capture_output=True, text=True, check=True, timeout=60,
        ).stdout
        items = json.loads(out or "[]")
    except (subprocess.SubprocessError, OSError, ValueError):
        return None
    counted = [i for i in items if i.get("stateReason") != "NOT_PLANNED"]
    done = sum(1 for i in counted if i.get("state") == "CLOSED" and i.get("stateReason") in ("COMPLETED", None))
    url = re.sub(r"/issues/\d+$", "/issues", items[0]["url"]) if items else ""
    return done, len(counted), url


def values(root: Path, issues: tuple[int, int, str] | None) -> dict[str, str]:
    """README '결과 한눈에' 항목 → 값 문자열 (검사기와 채우기가 같은 식을 쓴다)."""
    read = lambda rel: (root / rel).read_text(encoding="utf-8") if (root / rel).exists() else ""
    r, t, s = count_reqs(read("docs/prd.md")), count_tcs(read("docs/e2e-test.md")), count_secs(read("docs/security-compliance.md"))
    v = {
        "요구사항": f"검증됨 {r['verified']} / 전체 {r['total']} (주최 {r['host']} · 팀 {r['team']})",
        "시험": f"PASS {t['PASS']} · FAIL {t['FAIL']} · SKIP {t['SKIP']} · 미실행 {t['미실행']}",
        "보안": " · ".join(f"{k} {s[k]}" for k in SEC_STATES),
    }
    if issues:
        v["완료 Issue"] = f"{issues[0]} / {issues[1]}"
    return v


def fill_readme(text: str, v: dict[str, str], issues_url: str = "") -> tuple[str, list[str]]:
    lines, changed = text.splitlines(), []
    for _, header, rows in tables(text):
        if header != README_HEADER:
            continue
        for n, cells in rows:
            key = cells[0] if cells else ""
            if key in v and len(cells) >= 3 and cells[1] != v[key]:
                changed.append(f"{key}: {cells[1]} → {v[key]}")
                cells[1] = v[key]
                if key == "완료 Issue" and issues_url and "{{" in cells[2]:
                    cells[2] = f"[Issues]({issues_url})"
                lines[n] = "| " + " | ".join(cells) + " |"
        break
    return "\n".join(lines) + ("\n" if text.endswith("\n") else ""), changed


def fill_compliance_summary(text: str, s: dict[str, int]) -> tuple[str, list[str]]:
    lines, changed = text.splitlines(), []
    for _, header, rows in tables(text):
        if header != ["상태", "개수"]:
            continue
        for n, cells in rows:
            if len(cells) == 2 and cells[0] in s and cells[1] != str(s[cells[0]]):
                changed.append(f"{cells[0]}: {cells[1]} → {s[cells[0]]}")
                lines[n] = f"| {cells[0]} | {s[cells[0]]} |"
        break
    return "\n".join(lines) + ("\n" if text.endswith("\n") else ""), changed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    root = Path(args.root)
    readme, comp = root / "README.md", root / "docs/security-compliance.md"
    if not (root / "docs/prd.md").exists():
        print("  docs/prd.md 없음 — 결과 요약 건너뜀 (제출 문서가 없는 레포)")
        return 0
    issues = count_issues()
    v = values(root, issues)
    total: list[str] = []
    if readme.exists():
        new, changed = fill_readme(readme.read_text(encoding="utf-8"), v, issues[2] if issues else "")
        if changed and not args.dry_run:
            readme.write_text(new, encoding="utf-8")
        total += [f"README.md {c}" for c in changed]
    if comp.exists():
        new, changed = fill_compliance_summary(comp.read_text(encoding="utf-8"), count_secs(comp.read_text(encoding="utf-8")))
        if changed and not args.dry_run:
            comp.write_text(new, encoding="utf-8")
        total += [f"security-compliance.md 요약 {c}" for c in changed]
    for c in total:
        print(f"  {c}")
    if not total:
        print("  README·요약 숫자: 문서와 이미 같음")
    if issues is None:
        print("  (완료 Issue 칸은 gh 조회가 안 돼 그대로 둠)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
