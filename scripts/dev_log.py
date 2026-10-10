#!/usr/bin/env python3
"""AI 활용 기록 — 머지된 PR의 AI 리뷰 블록에서 docs/development.md 3절 표의 행을 만든다.

    python3 scripts/dev_log.py [--doc docs/development.md] [--dry-run]

행마다: 작업(연결된 Issue 제목), AI가 한 것(PR·AI 리뷰 점수), 사람이 확인한 방법(PR 본문의 '- AI 검증: …' 줄 + ship 검사·e2e·리뷰 지적 반영·머지한 사람),
고친 것(리뷰가 지적하고 다음 라운드에 '해결'로 판정된 것 — AI가 틀린 것을 잡은 근거), 근거(PR·머지 SHA).
이미 적힌 PR(근거 칸의 'PR #N' 또는 '/pull/N')은 건너뛰고, 양식의 {{자리표시}} 행은 첫 실제 행으로 바꾼다. 사람은 '사람이 확인한 방법' 칸에 직접 본 것을 보탠다.
make record가 부른다 (기록 담당 한 사람이 main에서 — 기능 PR끼리 같은 표를 고쳐 충돌하지 않게). 문서가 없는 레포(키트 원본)는 건너뛴다.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
START, END = "<!-- ai-review:start -->", "<!-- ai-review:end -->"
SECTION = "## 3. AI 활용 기록"
RECORD_TITLE = "docs(e2e): 시험 기록"  # make record가 만든 PR — 기계적 기록이라 AI 활용 사례가 아니다


def cell(text: str, limit: int = 120) -> str:
    s = re.sub(r"\s+", " ", str(text)).replace("|", "/").strip()
    return s if len(s) <= limit else s[: limit - 1] + "…"


def parse_review(body: str) -> dict:
    """마지막 AI 리뷰 블록 → {score, fixed:[...], open:[...]}. 블록이 없으면 score None.
    ship이 블록을 덮어쓰므로 '이전 지적 처리'는 마지막 라운드 기준이다 — 3라운드 이상에서 1라운드 지적이 2라운드에 해결된 것은 남지 않는다 (한계)."""
    blocks = re.findall(re.escape(START) + r"(.*?)" + re.escape(END), body or "", re.DOTALL)
    if not blocks:
        return {"score": None, "fixed": [], "open": []}
    blk = blocks[-1]
    m = re.search(r"총점:\s*(\d+)/60", blk)
    score = int(m.group(1)) if m else None

    def rows(section: str) -> list[list[str]]:
        sec = re.search(r"### " + re.escape(section) + r"\n(.*?)(?:\n###|\Z)", blk, re.DOTALL)
        out = []
        for line in (sec.group(1) if sec else "").splitlines():
            if not line.strip().startswith("|"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if cells and cells[0] not in ("#", "심각도") and not set(cells[0]) <= {"-"}:
                out.append(cells)
        return out

    fixed = [f"{r[1]}: {r[2]}" for r in rows("이전 지적 처리") if len(r) >= 4 and r[3] == "해결"]
    open_ = [f"{r[0]}: {r[2]}" for r in rows("지적 사항") if len(r) >= 3 and r[0] in ("차단", "높음", "중간", "낮음") and r[2] != "없음"]
    return {"score": score, "fixed": fixed, "open": open_}


_titles: dict[int, str] = {}


def issue_title(n: int) -> str:  # gh pr list의 closingIssuesReferences에는 제목이 없다 — 필요할 때만 한 번 조회
    if n not in _titles:
        try:
            _titles[n] = subprocess.run(["gh", "issue", "view", str(n), "--json", "title", "-q", ".title"],
                                        capture_output=True, text=True, check=True).stdout.strip()
        except (subprocess.CalledProcessError, OSError):
            _titles[n] = ""
    return _titles[n]


def human_notes(body: str) -> list[str]:
    """PR 본문(자동 블록 밖)의 '- AI 검증: …' 줄 — 사람이 AI 결과를 어떻게 확인·고쳤는지."""
    text = re.sub(re.escape(START) + r".*?" + re.escape(END), "", body or "", flags=re.DOTALL)
    text = re.sub(r"<!-- ship:start -->.*?<!-- ship:end -->", "", text, flags=re.DOTALL)
    return [m.group(1).strip() for m in re.finditer(r"(?m)^\s*[-*]?\s*AI 검증\s*:\s*(.+)$", text) if m.group(1).strip()]


def make_row(pr: dict, index: int) -> list[str]:
    rv = parse_review(pr.get("body") or "")
    issues = pr.get("closingIssuesReferences") or []
    task = (issues[0].get("title") or issue_title(issues[0]["number"]) or pr["title"]) if issues else pr["title"]
    issue_ref = f" (#{issues[0]['number']})" if issues else ""
    score = f"AI 리뷰 {rv['score']}/60" if rv["score"] is not None else "AI 리뷰 없음"
    merged_by = (pr.get("mergedBy") or {}).get("login") or "?"
    # ship이 검사를 끝내고 5단계에서 채운 확인 절("## 확인 (make ship 자동 기록")이 있을 때만 '검사·e2e 통과'라고 쓴다.
    # 1단계의 자리표시 블록("(make ship 검사 중)")만 있는 PR(검사에서 멈춘 뒤 사람이 머지)이나 손으로 만든 PR에는 없는 검사를 적지 않는다
    shipped = "make ship 검사·e2e 통과" if "## 확인 (make ship 자동 기록" in (pr.get("body") or "") else "ship 검사 기록 없음"
    checked = f"{shipped}, {score}" + (f" — 지적 {len(rv['fixed'])}건 반영" if rv["fixed"] else "") + f", 머지 {merged_by}"
    notes = human_notes(pr.get("body") or "")
    if notes:
        checked = "; ".join(notes) + f" ({checked})"  # 사람이 적은 확인이 앞에
    fixed = "<br>".join(cell(f, 80) for f in rv["fixed"]) if rv["fixed"] else "없음"
    sha = (pr.get("mergeCommit") or {}).get("oid", "")[:7]
    evidence = f"[PR #{pr['number']}]({pr['url']})" + (f" · `{sha}`" if sha else "")
    done = f"PR #{pr['number']}: {pr['title']}" if issues else f"PR #{pr['number']} 구현·리뷰"  # Issue가 없으면 작업 칸이 PR 제목이라 되풀이하지 않는다
    return [str(index), cell(task + issue_ref), cell(f"{done} — {score}"), cell(checked), fixed, evidence]


def recorded_prs(text: str) -> set[int]:
    _, _, rows_, _ = find_table(text)
    out: set[int] = set()
    for r in rows_:
        if r and "{{" not in "".join(r):
            # 근거 칸의 'PR #N'·'/pull/N'만 PR 번호로 본다 — 사람이 적은 Issue 번호(#N)나 SHA는 PR이 아니다
            out |= {int(n) for n in re.findall(r"PR #(\d+)|/pull/(\d+)", r[-1]) for n in n if n}
    return out


def find_table(text: str) -> tuple[int, int, list[list[str]], list[str]]:
    """3절의 첫 표 → (헤더 줄 번호, 표 끝 다음 줄 번호, 행들, 줄 목록). 없으면 (-1, -1, [], lines)."""
    lines = text.splitlines()
    try:
        start = next(i for i, l in enumerate(lines) if l.strip().startswith(SECTION))
    except StopIteration:
        return -1, -1, [], lines
    i = start + 1
    while i < len(lines) and not (lines[i].lstrip().startswith("|") and i + 1 < len(lines) and "---" in lines[i + 1]):
        if lines[i].startswith("## "):
            return -1, -1, [], lines
        i += 1
    if i >= len(lines):
        return -1, -1, [], lines
    j = i + 2
    rows_ = []
    while j < len(lines) and lines[j].lstrip().startswith("|"):
        rows_.append([c.strip() for c in lines[j].strip().strip("|").split("|")])
        j += 1
    return i, j, rows_, lines


def insert_rows(text: str, prs: list[dict]) -> tuple[str, int]:
    """머지 순서대로, 아직 없는 PR만 표 끝에 붙인다. 양식의 {{자리표시}} 행은 지운다."""
    hdr, end, rows_, lines = find_table(text)
    if hdr < 0:
        raise SystemExit(f"development.md에 '{SECTION}' 표가 없음 — 양식(templates/submission/docs/development.md) 3절을 확인")
    have = recorded_prs(text)
    real = [r for r in rows_ if "{{" not in "".join(r)]
    new = []
    n = len(real)
    for pr in sorted(prs, key=lambda p: p.get("mergedAt") or ""):
        if pr["number"] in have or pr["title"].startswith(RECORD_TITLE):
            continue
        n += 1
        new.append("| " + " | ".join(make_row(pr, n)) + " |")
    if not new:
        return text, 0
    kept = [l for l in lines[hdr + 2 : end] if "{{" not in l]
    out = lines[: hdr + 2] + kept + new + lines[end:]
    return "\n".join(out) + ("\n" if text.endswith("\n") else ""), len(new)


def merged_prs() -> list[dict]:
    out = subprocess.run(
        ["gh", "pr", "list", "--state", "merged", "--limit", "200", "--json",
         "number,title,body,mergedAt,mergeCommit,mergedBy,closingIssuesReferences,url"],
        capture_output=True, text=True, check=True,
    ).stdout
    return json.loads(out or "[]")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc", default=str(ROOT / "docs" / "development.md"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    doc = Path(args.doc)
    if not doc.exists():
        print("  docs/development.md 없음 — AI 활용 기록 건너뜀 (제출 문서가 없는 레포)")
        return 0
    text = doc.read_text(encoding="utf-8")
    try:
        prs = merged_prs()
    except (subprocess.CalledProcessError, OSError) as e:
        print(f"  ⚠️ 머지된 PR 조회 실패 — AI 활용 기록을 갱신하지 못함: {e}", file=sys.stderr)
        return 2
    new_text, n = insert_rows(text, prs)
    if n and not args.dry_run:
        doc.write_text(new_text, encoding="utf-8")
    print(f"  development.md AI 활용 기록: {n}행 추가" + (" (dry-run)" if args.dry_run else "") + " — '사람이 확인한 방법'에 직접 본 것을 보태세요")
    return 0


if __name__ == "__main__":
    sys.exit(main())
