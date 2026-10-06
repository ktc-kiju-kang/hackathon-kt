#!/usr/bin/env python3
"""PR 자동 점검 채점 (표준 라이브러리만). 설계: docs/superpowers/specs/2026-10-03-pr-review-scoring-design.md

PR 제목·본문·파일명·린트 메시지는 신뢰할 수 없는 입력이다. 정규식·JSON으로 읽기만 하고
셸·eval·템플릿에 끼워 넣지 않는다. 항상 종료 코드 0 (비차단).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

MARKER = "<!-- pr-review-score -->"
AUTO_MAX = 40
AI_MAX = 60
AI_ITEMS = {
    "정확성": 15,
    "보안·비밀값": 10,
    "계약·스키마 일치": 10,
    "설계·구조": 10,
    "테스트 품질": 10,
    "배포·운영 안전": 5,
}
AI_SECTIONS = ["변경 요약", "구조·설계 평가", "위험 분석", "테스트 평가", "지적 사항", "확인하지 못한 것"]
EXEMPT_TYPES = ("docs", "chore", "ci")

UI_PREFIX = "frontend/src/components/ui/"
CODE_RE = re.compile(r"^(backend/app/.+\.py|frontend/src/.+\.(ts|tsx))$")
TEST_RE = re.compile(r"^(backend/tests/.+|.+\.test\.(ts|tsx))$")
SIZE_EXCLUDE = ("package-lock.json", UI_PREFIX, "backend/data/")
CONTRACT_RE = re.compile(
    r"^(backend/app/(routers|schemas)/.+\.py|frontend/src/features/[^/]+/api\.ts)$"
)
COMMIT_RE = re.compile(r"^(feat|fix|refactor|docs|chore|test|perf|ci)(\([^)]+\))?: ")


def is_test(path: str) -> bool:
    return bool(TEST_RE.match(path))


def is_code(path: str) -> bool:
    return bool(CODE_RE.match(path)) and not path.startswith(UI_PREFIX) and not is_test(path)


def is_size_excluded(path: str) -> bool:
    return any(x in path for x in SIZE_EXCLUDE)


def is_contract_affecting(path: str) -> bool:
    return bool(CONTRACT_RE.match(path))


@dataclass
class Item:
    name: str
    score: int
    max: int
    note: str = ""
    measured: bool = True


def score_issue(title: str, body: str) -> Item:
    m = re.match(r"^(\w+)(\([^)]*\))?:", title)
    if m and m.group(1) in EXEMPT_TYPES:
        return Item("이슈 연결", 6, 6, "면제 (docs·chore·ci)")
    if re.search(r"\b(closes|fixes|resolves)\s+#\d+", body, re.I):
        return Item("이슈 연결", 6, 6, "Closes/Fixes 있음")
    if re.search(r"#\d+", body):
        return Item("이슈 연결", 4, 6, "참조만 있음 (Closes 권장)")
    return Item("이슈 연결", 0, 6, "이슈 연결 없음")


def _lines(f: dict) -> int:
    return f.get("additions", 0) + f.get("deletions", 0)


def score_tests(files: list[dict]) -> Item:
    code = [f for f in files if is_code(f["filename"])]
    if not code:
        return Item("테스트 동반", 8, 8, "코드 변경 없음")
    if any(is_test(f["filename"]) for f in files):
        return Item("테스트 동반", 8, 8, "테스트 변경 있음")
    n = sum(_lines(f) for f in code)
    if n <= 30:
        return Item("테스트 동반", 5, 8, f"코드 {n}줄 변경, 테스트 없음 (소규모)")
    return Item("테스트 동반", 0, 8, f"코드 {n}줄 변경, 테스트 없음")


def score_contract(files: list[dict]) -> Item:
    paths = [f["filename"] for f in files]
    affected = any(is_contract_affecting(p) for p in paths)
    changed = any(p.startswith("docs/contracts/") for p in paths)
    if affected and not changed:
        return Item("문서·계약 동반", 0, 5, "API 파일이 바뀌었는데 docs/contracts 변경 없음")
    return Item("문서·계약 동반", 5, 5, "해당 없음 또는 함께 변경")


def score_size(files: list[dict]) -> Item:
    n = sum(_lines(f) for f in files if not is_size_excluded(f["filename"]))
    pts = 4 if n <= 400 else 2 if n <= 800 else 0
    return Item("PR 크기", pts, 4, f"{n}줄 (제외 파일 뺌)")


def score_commits(messages: list[str]) -> Item:
    msgs = [m.split("\n", 1)[0] for m in messages if not m.startswith("Merge ")]
    if not msgs:
        return Item("커밋 규약", 3, 3, "대상 커밋 없음")
    ok = sum(1 for m in msgs if COMMIT_RE.match(m))
    return Item("커밋 규약", int(3 * ok / len(msgs) + 0.5), 3, f"{ok}/{len(msgs)}개 규약 준수")


def score_body(body: str) -> Item:
    pts = 0
    notes = []
    if len(body.strip()) >= 200:
        pts += 1
    else:
        notes.append("본문 200자 미만")
    if re.search(r"^##\s*변경", body, re.M):
        pts += 1
    else:
        notes.append("`## 변경` 없음")
    m = re.search(r"^##\s*(검증|확인)[^\n]*\n(.*?)(?=^##\s|\Z)", body, re.M | re.S)
    if m and re.search(r"^\s*([-*]|\d+\.)\s+\S", m.group(2), re.M):
        pts += 2
    else:
        notes.append("`## 검증` 항목 없음")
    return Item("PR 본문 충실도", pts, 4, ", ".join(notes) or "충실")


def _lint_item(name, mx, applicable, value, points, note):
    if not applicable:
        return Item(name, mx, mx, "해당 없음")
    if value is None:
        return Item(name, 0, mx, "측정 못 함", measured=False)
    return Item(name, points(value), mx, note(value))


def score_lint(frontend, backend, eslint_errors, ruff_violations, format_ok, ty_count):
    """측정값이 None이면 측정 못 함. 해당 영역 변경이 없으면 실행하지 않고 만점."""
    n = lambda v: f"{v}건"  # noqa: E731
    return [
        _lint_item("ESLint", 3, frontend, eslint_errors, lambda v: 3 if v == 0 else 0, n),
        _lint_item("ruff check", 3, backend, ruff_violations, lambda v: 3 if v == 0 else 0, n),
        _lint_item("ruff format", 2, backend, format_ok, lambda v: 2 if v else 0,
                   lambda v: "차이 없음" if v else "포맷 차이 있음"),
        _lint_item("ty", 2, backend, ty_count, lambda v: 2 if v == 0 else 1 if v <= 2 else 0, n),
    ]


def auto_total(items: list[Item]) -> tuple[int, list[str]]:
    """측정된 항목만으로 40점 만점에 비례 환산한다. 측정 못 한 항목 이름도 돌려준다."""
    got = [i for i in items if i.measured]
    missing = [i.name for i in items if not i.measured]
    mx = sum(i.max for i in got)
    if mx == 0:
        return 0, missing
    return int(sum(i.score for i in got) / mx * AUTO_MAX + 0.5), missing


@dataclass
class AiReview:
    total: int = 0
    commit: str = ""
    blocking: int = 0
    scores: dict | None = None
    errors: list | None = None
    warnings: list | None = None


def parse_ai_block(body: str) -> AiReview:
    r = AiReview(scores={}, errors=[], warnings=[])
    m = re.search(r"<!-- ai-review:start -->(.*?)<!-- ai-review:end -->", body, re.S)
    if not m:
        r.errors.append("AI 리뷰 블록이 없음")
        return r
    blk = m.group(1)
    c = re.search(r"리뷰한 커밋:\s*`?([0-9a-f]{7,40})`?", blk)
    if c:
        r.commit = c.group(1)
    else:
        r.errors.append("`리뷰한 커밋`이 없거나 형식이 틀림")
    t = re.search(r"총점:\s*(\d+)\s*/\s*60", blk)
    if t:
        r.total = int(t.group(1))
    else:
        r.errors.append("`총점: N/60`이 없거나 형식이 틀림")
    b = re.search(r"차단 이슈:\s*(없음|(\d+)\s*건)", blk)
    if b:
        r.blocking = int(b.group(2)) if b.group(2) else 0
    else:
        r.errors.append("`차단 이슈`가 없거나 형식이 틀림")
    for name, mx in AI_ITEMS.items():
        row = re.search(rf"\|\s*{re.escape(name)}\s*\|\s*(\d+)\s*/\s*(\d+)\s*\|", blk)
        if not row:
            r.errors.append(f"항목 `{name}` 점수가 없음")
            continue
        score, den = int(row.group(1)), int(row.group(2))
        if den != mx or score > mx:
            r.errors.append(f"항목 `{name}`이 배점 {mx}을 벗어남 ({score}/{den})")
        r.scores[name] = score
    if len(r.scores) == len(AI_ITEMS) and t and sum(r.scores.values()) != r.total:
        r.errors.append(f"항목 합({sum(r.scores.values())})과 총점({r.total})이 다름")
    for h in AI_SECTIONS:
        if not re.search(rf"^#{{2,4}}\s*{re.escape(h)}", blk, re.M):
            r.warnings.append(f"섹션 `{h}` 없음")
    return r


def commits_behind(reviewed: str, shas: list[str]) -> int | None:
    """리뷰한 커밋 뒤에 쌓인 커밋 수. PR에 없으면 None."""
    for i, sha in enumerate(shas):
        if sha.startswith(reviewed):
            return len(shas) - 1 - i
    return None


def verdict(total: int, blocking: int, ai_ok: bool) -> str:
    if not ai_ok:
        return "AI 리뷰 필요"
    if blocking > 0 or total < 70:
        return "수정 필요"
    return "머지 가능" if total >= 85 else "지적 처리 후 머지"


def sanitize(text: str, limit: int = 200) -> str:
    """코멘트에 인용할 외부 문자열: 멘션·링크·HTML을 무력화하고 한 줄로 줄인다."""
    t = " ".join(str(text).split())
    t = t.replace("@", "@​").replace("](", "]​(").replace("<", "&lt;")
    return t if len(t) <= limit else t[:limit] + "…"


def render_comment(
    items: list[Item],
    auto: int,
    missing: list[str],
    ai: AiReview | None,
    behind: int | None,
    head_sha: str,
) -> str:
    ai_ok = ai is not None and not ai.errors
    total = auto + (ai.total if ai_ok else 0)
    v = verdict(total, ai.blocking if ai_ok else 0, ai_ok)
    stale = ai_ok and behind is not None and behind > 0
    lines = [MARKER, "## PR 리뷰 점수", ""]
    if ai_ok:
        suffix = " (최신 아님)" if stale else ""
        lines.append(f"**{total}/100 — {v}**{suffix}  (자동 {auto}/40 + AI {ai.total}/60)")
    else:
        lines.append(f"**자동 점검 {auto}/40 — {v}**")
    lines += ["", "### 자동 점검", "| 항목 | 점수 | 비고 |", "|---|---|---|"]
    for i in items:
        score = f"{i.score}/{i.max}" if i.measured else "—"
        lines.append(f"| {i.name} | {score} | {sanitize(i.note, 120)} |")
    if missing:
        lines += ["", f"측정 못 한 항목({', '.join(missing)})은 제외하고 비율로 환산했습니다."]
    lines += ["", "### AI 리뷰"]
    no_block = ai is None or ai.errors == ["AI 리뷰 블록이 없음"]
    if no_block:
        lines.append("PR 본문에 AI 리뷰 블록이 없습니다. `/handoff`로 리뷰를 받아 본문에 넣으세요.")
    elif ai.errors:
        lines.append("형식 오류로 AI 점수는 0점입니다:")
        lines += [f"- {sanitize(e, 160)}" for e in ai.errors]
    else:
        lines.append(f"리뷰한 커밋 `{sanitize(ai.commit, 40)}`, 차단 이슈 {ai.blocking}건")
        if behind is None:
            lines.append("- ⚠️ 리뷰한 커밋이 이 PR에 없습니다.")
        elif behind > 0:
            lines.append(f"- ⚠️ 리뷰 이후 {behind}개 커밋이 추가됐습니다. 다시 리뷰하세요.")
        lines += [f"- ⚠️ {sanitize(w, 100)}" for w in (ai.warnings or [])]
    lines += [
        "",
        f"<sub>head `{head_sha[:7]}` · 점수는 참고용이며 머지 결정은 사람이 합니다. "
        "AI 리뷰는 작성자의 자기 보고라 실제 실행 여부는 검증하지 못합니다.</sub>",
    ]
    return "\n".join(lines) + "\n"
