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
AI_SECTIONS = [
    "변경 요약",
    "구조·설계 평가",
    "위험 분석",
    "테스트 평가",
    "지적 사항",
    "확인하지 못한 것",
]
EXEMPT_TYPES = ("docs", "chore", "ci")

UI_PREFIX = "frontend/src/components/ui/"
CODE_RE = re.compile(r"^(backend/app/.+\.py|frontend/src/.+\.(ts|tsx))$")
TEST_RE = re.compile(r"^(backend/tests/.+|.+\.test\.(ts|tsx))$")
SIZE_EXCLUDE_NAMES = ("package-lock.json",)
SIZE_EXCLUDE_PREFIXES = (UI_PREFIX, "backend/data/")
CONTRACT_RE = re.compile(
    r"^(backend/app/(routers|schemas)/.+\.py|frontend/src/features/[^/]+/api\.ts)$"
)
COMMIT_RE = re.compile(r"^(feat|fix|refactor|docs|chore|test|perf|ci)(\([^)]+\))?: ")
AI_BLOCK_RE = re.compile(r"<!-- ai-review:start -->(.*?)<!-- ai-review:end -->", re.DOTALL)


def is_test(path: str) -> bool:
    return bool(TEST_RE.match(path))


def is_code(path: str) -> bool:
    return bool(CODE_RE.match(path)) and not path.startswith(UI_PREFIX) and not is_test(path)


def is_size_excluded(path: str) -> bool:
    return path.rsplit("/", 1)[-1] in SIZE_EXCLUDE_NAMES or path.startswith(SIZE_EXCLUDE_PREFIXES)


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
    kw = r"\b(?:close[sd]?|fix(?:es|ed)?|resolve[sd]?):?\s+(?:[\w.-]+/[\w.-]+)?#\d+"
    if re.search(kw, body, re.IGNORECASE):
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
    if re.search(r"^##\s*변경", body, re.MULTILINE):
        pts += 1
    else:
        notes.append("`## 변경` 없음")
    m = re.search(r"^##\s*(검증|확인)[^\n]*\n(.*?)(?=^##\s|\Z)", body, re.MULTILINE | re.DOTALL)
    if m and re.search(r"^\s*([-*]|\d+\.)\s+\S", m.group(2), re.MULTILINE):
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
    n = lambda v: f"{v}건"
    return [
        _lint_item("ESLint", 3, frontend, eslint_errors, lambda v: 3 if v == 0 else 0, n),
        _lint_item("ruff check", 3, backend, ruff_violations, lambda v: 3 if v == 0 else 0, n),
        _lint_item(
            "ruff format",
            2,
            backend,
            format_ok,
            lambda v: 2 if v else 0,
            lambda v: "차이 없음" if v else "포맷 차이 있음",
        ),
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
    blocks = AI_BLOCK_RE.findall(body)  # 본문 앞쪽 예시·플레이스홀더보다 마지막 블록을 쓴다
    if not blocks:
        r.errors.append("AI 리뷰 블록이 없음")
        return r
    blk = blocks[-1]
    c = re.search(r"리뷰한 커밋:\s*`?([0-9a-f]{7,40})(?![0-9A-Za-z])`?", blk)
    if c:
        r.commit = c.group(1)
    else:
        r.errors.append("`리뷰한 커밋`이 없거나 형식이 틀림")
    t = re.search(r"총점:\s*(\d+)\s*/\s*60\b", blk)
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
        if not re.search(rf"^#{{2,4}}\s*{re.escape(h)}", blk, re.MULTILINE):
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
    t = t.replace("&", "&amp;").replace("<", "&lt;")  # & 를 먼저
    t = t.replace("@", "@\u200b").replace("](", "]\u200b(")
    t = t.replace("://", ":\u200b//")  # 자동 링크 무력화
    t = t.replace("|", "\\|")  # 표 셀 깨짐 방지
    t = re.sub(r"#(?=\d)", "#\u200b", t)  # 이슈·PR 자동 참조 무력화
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
        lines.append(
            "PR 본문에 AI 리뷰 블록이 없습니다. `/handoff`로 리뷰를 받아 본문에 넣으세요."
        )
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
        (
            f"<sub>head `{head_sha[:7]}` · 점수는 참고용이며 머지 결정은 사람이 합니다. "
            "AI 리뷰는 작성자의 자기 보고라 실제 실행 여부는 검증하지 못합니다.</sub>"
        ),
    ]
    return "\n".join(lines) + "\n"


def _read_json(path: Path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def count_eslint(d: Path) -> int | None:
    data = _read_json(d / "eslint.json")
    if not isinstance(data, list):
        return None
    return sum(int(f.get("errorCount", 0)) for f in data)


def count_ruff(d: Path) -> int | None:
    data = _read_json(d / "ruff.json")
    return len(data) if isinstance(data, list) else None


def format_ok(d: Path) -> bool | None:
    """종료 코드 0=차이 없음, 1=차이 있음. 그 외(2·127 등)는 도구 실패이므로 측정 못 함."""
    try:
        code = (d / "ruff-format.code").read_text().strip()
    except OSError:
        return None
    return {"0": True, "1": False}.get(code)


def count_ty(d: Path) -> int | None:
    try:
        text = (d / "ty.txt").read_text()
    except OSError:
        return None
    counted = len(re.findall(r"^\S+:\d+:\d+: (?:error|warning)\[", text, re.MULTILINE))
    found = re.search(r"^Found (\d+) diagnostics?\b", text, re.MULTILINE)
    if found:  # 요약 줄의 N이 있으면 우선
        return int(found.group(1))
    if re.search(r"^All checks passed!", text, re.MULTILINE):
        return counted
    return None  # 정상 종료 표식이 없으면 도구 실패로 보고 0건으로 오인하지 않는다


# ---- GitHub I/O (gh CLI) ----------------------------------------------------


def gh(*args: str, stdin: str | None = None) -> str:
    return subprocess.run(
        ["gh", *args], input=stdin, capture_output=True, text=True, check=True
    ).stdout


def gh_pages(path: str) -> list:
    """페이지가 여러 개여도 하나의 목록으로 합친다."""
    pages = json.loads(gh("api", "--paginate", "--slurp", path))
    return [x for page in pages for x in page]


def load_pr() -> tuple[str, int, dict]:
    repo = os.environ["GITHUB_REPOSITORY"]
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    number = event["pull_request"]["number"]
    pr = json.loads(gh("api", f"repos/{repo}/pulls/{number}"))
    return repo, number, pr


def detect_areas(files: list[dict]) -> tuple[bool, bool]:
    names = [f["filename"] for f in files]
    return any(n.startswith("frontend/") for n in names), any(
        n.startswith("backend/") for n in names
    )


def _is_mine(c: dict) -> bool:
    """봇이 쓴 마커 코멘트만. 사용자가 마커를 흉내 낸 코멘트는 건드리지 않는다."""
    user = c.get("user") or {}
    is_bot = user.get("type") == "Bot" or user.get("login") == "github-actions[bot]"
    return is_bot and MARKER in (c.get("body") or "")


def upsert_comment(repo: str, number: int, body: str) -> None:
    comments = gh_pages(f"repos/{repo}/issues/{number}/comments")
    mine = next((c for c in comments if _is_mine(c)), None)
    if mine:
        gh(
            "api",
            "-X",
            "PATCH",
            f"repos/{repo}/issues/comments/{mine['id']}",
            "-f",
            f"body={body}",
        )
    else:
        gh("api", f"repos/{repo}/issues/{number}/comments", "-f", f"body={body}")


def write_output(name: str, value: str) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a") as f:
            f.write(f"{name}={value}\n")


def main(argv: list[str]) -> None:
    repo, number, pr = load_pr()
    files = gh_pages(f"repos/{repo}/pulls/{number}/files")
    frontend, backend = detect_areas(files)
    if "--areas" in argv:  # 워크플로가 린트를 어느 영역에서 돌릴지 정하는 용도
        write_output("frontend", str(frontend).lower())
        write_output("backend", str(backend).lower())
        return

    commits = gh_pages(f"repos/{repo}/pulls/{number}/commits")
    lint_dir = Path(argv[argv.index("--lint-dir") + 1]) if "--lint-dir" in argv else Path("lint")
    title, body = pr.get("title") or "", pr.get("body") or ""

    items = [
        *score_lint(
            frontend,
            backend,
            count_eslint(lint_dir) if frontend else None,
            count_ruff(lint_dir) if backend else None,
            format_ok(lint_dir) if backend else None,
            count_ty(lint_dir) if backend else None,
        ),
        score_issue(title, body),
        score_tests(files),
        score_contract(files),
        score_size(files),
        score_commits([c["commit"]["message"] for c in commits]),
        score_body(body),
    ]
    auto, missing = auto_total(items)

    ai = parse_ai_block(body)
    behind = None
    if not ai.errors:
        behind = commits_behind(ai.commit, [c["sha"] for c in commits])
        if behind is None:
            ai.errors.append("리뷰한 커밋이 이 PR에 없음")
    comment = render_comment(items, auto, missing, ai, behind, pr["head"]["sha"])

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        Path(summary).write_text(comment)
    try:
        upsert_comment(repo, number, comment)
    except (subprocess.CalledProcessError, ValueError) as e:
        # 읽기 전용 토큰(Dependabot·포크)은 요약만 남긴다. stderr 에 HTTP 상태가 들어 있다.
        detail = sanitize(getattr(e, "stderr", None) or str(e), 200)
        print(f"코멘트를 쓰지 못함(권한? {type(e).__name__}): {detail}")


def report_failure(e: Exception) -> None:
    """채점 자체가 실패했을 때 요약과 최소 코멘트를 최대한 남긴다. 절대 예외를 내지 않는다."""
    msg = f"채점 실패: {type(e).__name__}"
    print(f"{msg}: {sanitize(str(e), 300)}")
    try:
        summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary:
            Path(summary).write_text(f"## PR 리뷰 점수\n\n{msg}\n")
    except Exception as e2:  # noqa: BLE001
        print(f"요약을 쓰지 못함: {type(e2).__name__}")
    try:
        repo = os.environ["GITHUB_REPOSITORY"]
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
        upsert_comment(
            repo, event["pull_request"]["number"], f"{MARKER}\n## PR 리뷰 점수\n\n{msg}\n"
        )
    except Exception as e2:  # noqa: BLE001
        print(f"실패 코멘트를 쓰지 못함: {type(e2).__name__}")


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except Exception as e:  # noqa: BLE001  비차단: 채점 실패가 PR을 막지 않는다
        report_failure(e)
    sys.exit(0)
