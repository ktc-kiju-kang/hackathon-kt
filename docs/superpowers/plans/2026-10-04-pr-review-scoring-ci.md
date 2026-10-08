# PR 자동 점검 CI (PR 1/2) 구현 계획

> **상태: 미구현 (2026-10-06 확인)**. 아래 코드는 계획용 예시이며 저장소의 실행 파일이 아니다. 문서의 `Expected`와 체크리스트는 실제 실행 결과가 아니고, 이 문서 수정으로 워크플로가 설치되지 않는다. 현재 운영 절차는 [SDLC](../../SDLC.md)를 따른다.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** PR이 열리거나 갱신될 때 자동 점검 40점(이슈 연결·테스트·계약·커밋·본문·린트/타입)과 AI 리뷰 블록 검증 결과를 PR 코멘트 1개로 남긴다.

**Architecture:** 표준 라이브러리만 쓰는 `scripts/pr_review_score.py`가 `gh api`로 PR 메타·파일·커밋을 읽어 채점하고, 워크플로가 만든 린트 결과 파일(`lint/`)을 읽어 린트 점수를 낸다. 점수 함수는 전부 순수 함수라 `unittest`로 경계값을 검증한다. 워크플로는 보고 전용·비차단을 목표로 하며, 실패 시에도 보고를 남기는 처리는 아래 착수 전 재확인 대상이다. 설계: `docs/superpowers/specs/2026-10-03-pr-review-scoring-design.md`.

**Tech Stack:** Python 3 stdlib(unittest, re, json, subprocess), `gh` CLI, GitHub Actions, ESLint(JSON), ruff(JSON), ty(concise)

**범위 밖:** 리뷰 흐름 문서·`reviewer`/`/handoff`/PR 템플릿 갱신(PR 2, 이 PR 머지 후 별도 계획).

**브랜치:** `ci/pr-review-score` (이슈 없는 인프라 작업 규칙: `<type>/<설명>`)

## 구현 갱신

- 2026-10-07: PR 크기 항목 삭제(`score_size`·`is_size_excluded` 제거), 배점 재배분 — 테스트 동반 8→10(코드만 있고 테스트 없음·30줄 이하 = 6), PR 본문 충실도 4→6(길이 1·`## 변경` 2·`## 검증` 항목 3). 자동 합계는 40 유지. 아래 Task 2의 코드·테스트는 이전 설계 기준의 기록이며 다시 쓰지 않았다.

## 구현 착수 전 재확인

기존 배점·판정선을 바꾸는 절차가 아니라, 예시를 실제 구현으로 옮기기 전에 확인해야 할 차이다. **아래 코드 블록을 그대로 실행 가능한 완성본으로 취급하지 않는다.**

- [현재 CI](../../../.github/workflows/ci.yml)는 checkout·setup-node·setup-python v7을 사용한다. Task 7의 액션 버전은 예전 예시이므로 구현 시 현재 main과 맞춘다.
- 워크플로가 필수 체크가 아닌 것과 모든 step이 성공하는 것은 별개다. 설치 실패·API 실패·파싱 실패에도 상태가 명확히 보고되는지, 도구 실패를 진단 0건으로 오인하지 않는지 확인한다. 성공 경로 테스트만으로 "항상 성공"을 주장하지 않는다.
- PR이 바꾼 스크립트·의존성·린트 설정은 실행 코드다. Task 7처럼 작업 전체에 쓰기 토큰을 두는 예시를 그대로 채택하지 말고 실행 단계와 보고 단계의 권한 경계를 먼저 확정한다. 포크·Dependabot의 읽기 전용 경로도 별도로 검증한다.
- Task 8의 변이 시험은 격리된 임시 사본/worktree에서 한다. 원래 미커밋 변경이 있을 수 있는 작업 파일을 통째로 되돌리지 않는다. 생성한 변이만 제거하고 원래 내용이 보존됐는지 확인한다.
- 실환경 PR·push·수동 실행은 사용자 승인 후 진행한다. 기존 #55 같은 과거 PR이 여전히 열려 있다고 가정하지 말고 현재 사용할 수 있는 검증 대상을 확인한다.
- 미측정·해당 없음·오래된 AI 리뷰는 별도로 표시하고, 테스트·설치 실패를 숨겨 점수를 높이지 않는다. 실제 실행 URL·대상 SHA·명령·결과가 남기 전에는 체크박스를 완료로 바꾸지 않는다.

---

## 파일 구조

| 파일 | 역할 |
|---|---|
| `scripts/pr_review_score.py` | 분류·채점·AI 블록 파싱·최신성·렌더링·GitHub I/O (순수 함수 + `main`) |
| `scripts/test_pr_review_score.py` | 위 순수 함수의 단위 테스트 |
| `.github/workflows/pr-review.yml` | 영역 판단 → 린트 실행 → 채점 스크립트 실행 |

한 파일이 길어지지만 함수 단위로 분리되어 있고(채점 규칙 한 곳), 의존성 없이 `python3 scripts/pr_review_score.py`로 돈다.

---

### Task 1: 파일 분류 함수

**Files:**
- Create: `scripts/pr_review_score.py`
- Create: `scripts/test_pr_review_score.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`scripts/test_pr_review_score.py`:

```python
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pr_review_score as s  # noqa: E402


class ClassifyTest(unittest.TestCase):
    def test_is_code(self):
        self.assertTrue(s.is_code("backend/app/services/radar.py"))
        self.assertTrue(s.is_code("frontend/src/features/radar/api.ts"))
        self.assertFalse(s.is_code("backend/tests/test_radar.py"))
        self.assertFalse(s.is_code("frontend/src/lib/sse.test.ts"))
        self.assertFalse(s.is_code("frontend/src/components/ui/button.tsx"))
        self.assertFalse(s.is_code("docs/SDLC.md"))

    def test_is_test(self):
        self.assertTrue(s.is_test("backend/tests/test_radar.py"))
        self.assertTrue(s.is_test("frontend/src/lib/sse.test.ts"))
        self.assertFalse(s.is_test("backend/app/services/radar.py"))

    def test_size_excluded(self):
        self.assertTrue(s.is_size_excluded("frontend/package-lock.json"))
        self.assertTrue(s.is_size_excluded("frontend/src/components/ui/card.tsx"))
        self.assertTrue(s.is_size_excluded("backend/data/signals/x.csv"))
        self.assertFalse(s.is_size_excluded("backend/app/main.py"))

    def test_is_contract_affecting(self):
        self.assertTrue(s.is_contract_affecting("backend/app/routers/radar.py"))
        self.assertTrue(s.is_contract_affecting("backend/app/schemas/radar.py"))
        self.assertTrue(s.is_contract_affecting("frontend/src/features/radar/api.ts"))
        self.assertFalse(s.is_contract_affecting("backend/app/services/radar.py"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 실패 확인**

Run: `python3 scripts/test_pr_review_score.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'pr_review_score'`

- [ ] **Step 3: 최소 구현**

`scripts/pr_review_score.py`:

```python
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
```

- [ ] **Step 4: 통과 확인**

Run: `python3 scripts/test_pr_review_score.py`
Expected: `Ran 4 tests ... OK`

- [ ] **Step 5: 커밋**

```bash
git add scripts/pr_review_score.py scripts/test_pr_review_score.py
git commit -m "ci(review): PR 점수 스크립트 뼈대와 파일 분류 함수"
```

---

### Task 2: 자동 점검 6개 항목 채점

**Files:**
- Modify: `scripts/pr_review_score.py` (끝에 추가)
- Modify: `scripts/test_pr_review_score.py` (`if __name__` 위에 추가)

- [ ] **Step 1: 실패하는 테스트 작성**

`if __name__ == "__main__":` 바로 위에 추가:

```python
def F(path, add=0, dele=0):
    return {"filename": path, "additions": add, "deletions": dele}


class ScoreTest(unittest.TestCase):
    def test_issue(self):
        self.assertEqual(s.score_issue("docs: x", "").score, 6)  # 면제
        self.assertEqual(s.score_issue("chore(ci): x", "").score, 6)
        self.assertEqual(s.score_issue("feat(a): x", "Closes #12").score, 6)
        self.assertEqual(s.score_issue("fix: x", "fixes #3").score, 6)
        self.assertEqual(s.score_issue("feat: x", "관련 #9").score, 4)
        self.assertEqual(s.score_issue("feat: x", "없음").score, 0)

    def test_tests(self):
        self.assertEqual(s.score_tests([F("docs/a.md", 5)]).score, 8)  # 코드 변경 없음
        code, test = F("backend/app/a.py", 100), F("backend/tests/test_a.py", 10)
        self.assertEqual(s.score_tests([code, test]).score, 8)
        self.assertEqual(s.score_tests([F("backend/app/a.py", 30)]).score, 5)  # 30 이하
        self.assertEqual(s.score_tests([F("backend/app/a.py", 20, 11)]).score, 0)  # 31

    def test_contract(self):
        r, c = F("backend/app/routers/radar.py", 3), F("docs/contracts/radar.md", 3)
        self.assertEqual(s.score_contract([r]).score, 0)
        self.assertEqual(s.score_contract([r, c]).score, 5)
        self.assertEqual(s.score_contract([F("backend/app/services/radar.py")]).score, 5)

    def test_size(self):
        self.assertEqual(s.score_size([F("backend/app/a.py", 400)]).score, 4)
        self.assertEqual(s.score_size([F("backend/app/a.py", 401)]).score, 2)
        self.assertEqual(s.score_size([F("backend/app/a.py", 800)]).score, 2)
        self.assertEqual(s.score_size([F("backend/app/a.py", 801)]).score, 0)
        big = F("frontend/package-lock.json", 5000)
        self.assertEqual(s.score_size([F("backend/app/a.py", 10), big]).score, 4)  # 제외

    def test_commits(self):
        ok, bad = "feat(x): a", "수정함"
        self.assertEqual(s.score_commits([ok, ok, ok]).score, 3)
        self.assertEqual(s.score_commits([ok, ok, bad]).score, 2)  # 2/3*3=2
        self.assertEqual(s.score_commits([ok, bad, bad]).score, 1)
        self.assertEqual(s.score_commits([bad]).score, 0)
        self.assertEqual(s.score_commits(["Merge branch 'main'", ok]).score, 3)  # 머지 제외
        self.assertEqual(s.score_commits(["Merge branch 'main'"]).score, 3)  # 대상 없음

    def test_body(self):
        full = "## 변경\n" + "가" * 200 + "\n## 검증\n- npm test 통과\n"
        self.assertEqual(s.score_body(full).score, 4)
        self.assertEqual(s.score_body("짧음").score, 0)
        self.assertEqual(s.score_body("## 변경\n" + "가" * 200).score, 2)  # 길이+변경
        no_item = "## 변경\n" + "가" * 200 + "\n## 검증\n\n"
        self.assertEqual(s.score_body(no_item).score, 2)
        alt = "## 변경 내용\n" + "가" * 200 + "\n## 확인\n1. 해봄\n"
        self.assertEqual(s.score_body(alt).score, 4)
```

- [ ] **Step 2: 실패 확인**

Run: `python3 scripts/test_pr_review_score.py`
Expected: FAIL — `AttributeError: module 'pr_review_score' has no attribute 'score_issue'`

- [ ] **Step 3: 구현**

`pr_review_score.py` 끝에 추가:

```python
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
```

- [ ] **Step 4: 통과 확인**

Run: `python3 scripts/test_pr_review_score.py`
Expected: `OK` (테스트 10개)

- [ ] **Step 5: 커밋**

```bash
git add scripts/ && git commit -m "ci(review): 자동 점검 6개 항목 채점과 경계값 테스트"
```

---

### Task 3: 린트·타입 채점과 합산

**Files:** 같은 두 파일

- [ ] **Step 1: 실패하는 테스트 작성**

```python
class LintTest(unittest.TestCase):
    def names(self, items):
        return {i.name: i for i in items}

    def test_not_applicable_is_full(self):
        items = s.score_lint(False, False, None, None, None, None)
        self.assertTrue(all(i.score == i.max and i.measured for i in items))
        self.assertEqual(sum(i.max for i in items), 10)

    def test_frontend_eslint(self):
        d = self.names(s.score_lint(True, False, 0, None, None, None))
        self.assertEqual(d["ESLint"].score, 3)
        d = self.names(s.score_lint(True, False, 2, None, None, None))
        self.assertEqual(d["ESLint"].score, 0)

    def test_backend(self):
        d = self.names(s.score_lint(False, True, None, 0, True, 0))
        self.assertEqual([d[k].score for k in ("ruff check", "ruff format", "ty")], [3, 2, 2])
        d = self.names(s.score_lint(False, True, None, 4, False, 1))
        self.assertEqual([d[k].score for k in ("ruff check", "ruff format", "ty")], [0, 0, 1])
        d = self.names(s.score_lint(False, True, None, 0, True, 3))
        self.assertEqual(d["ty"].score, 0)

    def test_unmeasured(self):
        d = self.names(s.score_lint(True, False, None, None, None, None))
        self.assertFalse(d["ESLint"].measured)

    def test_total_scales_over_measured(self):
        items = [s.Item("a", 6, 6), s.Item("b", 0, 4, measured=False), s.Item("c", 0, 10)]
        total, missing = s.auto_total(items)
        self.assertEqual(total, 15)  # 6/16 * 40
        self.assertEqual(missing, ["b"])
        self.assertEqual(s.auto_total([s.Item("a", 5, 5, measured=False)]), (0, ["a"]))
```

- [ ] **Step 2: 실패 확인** — Run `python3 scripts/test_pr_review_score.py` → `AttributeError: ... 'score_lint'`

- [ ] **Step 3: 구현**

```python
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
```

- [ ] **Step 4: 통과 확인** — Run `python3 scripts/test_pr_review_score.py` → OK (테스트 15개)

- [ ] **Step 5: 커밋** — `git add scripts/ && git commit -m "ci(review): 린트·타입 채점과 측정된 항목 기준 환산"`

---

### Task 4: AI 리뷰 블록 파싱·검증·최신성·판정

**Files:** 같은 두 파일

- [ ] **Step 1: 실패하는 테스트 작성**

```python
def block(commit="abc1234", total=52, blocking="없음", scores=None, sections=True):
    scores = scores or [13, 10, 10, 8, 7, 4]
    rows = "\n".join(
        f"| {n} | {v}/{m} |" for (n, m), v in zip(s.AI_ITEMS.items(), scores)
    )
    secs = "\n".join(f"### {h}" for h in s.AI_SECTIONS) if sections else ""
    return (
        f"본문\n<!-- ai-review:start -->\n## AI 리뷰\n- 리뷰한 커밋: `{commit}`\n"
        f"- 총점: {total}/60\n- 판정: 지적 처리 후 머지\n- 차단 이슈: {blocking}\n\n"
        f"| 항목 | 점수 |\n|---|---|\n{rows}\n\n{secs}\n<!-- ai-review:end -->\n"
    )


class AiBlockTest(unittest.TestCase):
    def test_ok(self):
        r = s.parse_ai_block(block())
        self.assertEqual(r.errors, [])
        self.assertEqual((r.total, r.commit, r.blocking), (52, "abc1234", 0))

    def test_blocking_count(self):
        self.assertEqual(s.parse_ai_block(block(blocking="2건")).blocking, 2)

    def test_missing_block(self):
        r = s.parse_ai_block("블록 없음")
        self.assertTrue(r.errors)

    def test_sum_mismatch(self):
        self.assertTrue(s.parse_ai_block(block(total=50)).errors)

    def test_item_over_max(self):
        r = s.parse_ai_block(block(total=56, scores=[16, 10, 10, 8, 7, 5]))
        self.assertTrue(any("배점" in e for e in r.errors))

    def test_missing_item(self):
        text = block().replace("| 배포·운영 안전 | 4/5 |\n", "")
        self.assertTrue(s.parse_ai_block(text).errors)

    def test_bad_commit(self):
        self.assertTrue(s.parse_ai_block(block(commit="xyz")).errors)

    def test_missing_sections_are_warnings(self):
        r = s.parse_ai_block(block(sections=False))
        self.assertEqual(r.errors, [])
        self.assertEqual(len(r.warnings), len(s.AI_SECTIONS))

    def test_freshness(self):
        shas = ["aaa1111" + "0" * 33, "bbb2222" + "0" * 33, "ccc3333" + "0" * 33]
        self.assertEqual(s.commits_behind("ccc3333", shas), 0)
        self.assertEqual(s.commits_behind("aaa1111", shas), 2)
        self.assertIsNone(s.commits_behind("ddd4444", shas))

    def test_verdict(self):
        self.assertEqual(s.verdict(90, 0, True), "머지 가능")
        self.assertEqual(s.verdict(85, 0, True), "머지 가능")
        self.assertEqual(s.verdict(84, 0, True), "지적 처리 후 머지")
        self.assertEqual(s.verdict(70, 0, True), "지적 처리 후 머지")
        self.assertEqual(s.verdict(69, 0, True), "수정 필요")
        self.assertEqual(s.verdict(99, 1, True), "수정 필요")  # 차단 이슈
        self.assertEqual(s.verdict(40, 0, False), "AI 리뷰 필요")
```

- [ ] **Step 2: 실패 확인** — `AttributeError: ... 'parse_ai_block'`

- [ ] **Step 3: 구현**

```python
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
```

- [ ] **Step 4: 통과 확인** — `python3 scripts/test_pr_review_score.py` → OK (테스트 25개 내외)

- [ ] **Step 5: 커밋** — `git add scripts/ && git commit -m "ci(review): AI 리뷰 블록 파싱·검증, 최신성, 판정"`

---

### Task 5: 코멘트 렌더링과 입력 무력화

**Files:** 같은 두 파일

- [ ] **Step 1: 실패하는 테스트 작성**

```python
class RenderTest(unittest.TestCase):
    def test_sanitize(self):
        out = s.sanitize("@octocat [x](http://e.com) <script>\n줄바꿈", 200)
        self.assertNotIn("@octocat", out)
        self.assertNotIn("](", out)
        self.assertNotIn("<script>", out)
        self.assertNotIn("\n", out)
        self.assertEqual(len(s.sanitize("가" * 500, 100)), 101)  # 100 + …

    def _render(self, ai=None, behind=0):
        items = [s.Item("이슈 연결", 6, 6, "Closes 있음"), s.Item("ty", 0, 2, "측정 못 함", False)]
        return s.render_comment(items, 38, ["ty"], ai, behind, "abc1234")

    def test_marker_and_no_ai(self):
        out = self._render()
        self.assertTrue(out.startswith(s.MARKER))
        self.assertIn("AI 리뷰 필요", out)
        self.assertIn("38/40", out)
        self.assertIn("측정 못 함", out)

    def test_with_ai_and_stale(self):
        ai = s.parse_ai_block(block())
        out = self._render(ai, behind=2)
        self.assertIn("90/100", out)
        self.assertIn("최신 아님", out)
        self.assertIn("2개 커밋", out)

    def test_ai_errors_listed(self):
        ai = s.parse_ai_block(block(total=50))
        out = self._render(ai)
        self.assertIn("형식 오류", out)
        self.assertIn("항목 합", out)
```

- [ ] **Step 2: 실패 확인** — `AttributeError: ... 'sanitize'`

- [ ] **Step 3: 구현**

```python
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
```

참고: "리뷰한 커밋이 이 PR에 없음"은 spec상 형식 오류이므로 Task 6의 `main`에서 `commits_behind`가 None이면 `ai.errors`에 추가한 뒤 렌더링한다 (`render_comment`는 errors 목록을 그대로 보여 준다).

- [ ] **Step 4: 통과 확인** — `python3 scripts/test_pr_review_score.py` → OK

- [ ] **Step 5: 커밋** — `git add scripts/ && git commit -m "ci(review): 코멘트 렌더링과 외부 입력 무력화"`

---

### Task 6: GitHub I/O와 main

**Files:**
- Modify: `scripts/pr_review_score.py`
- Modify: `scripts/test_pr_review_score.py`

- [ ] **Step 1: 린트 결과 파서 테스트 작성**

```python
import json
import tempfile


class LintParseTest(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())

    def test_eslint(self):
        (self.d / "eslint.json").write_text(
            json.dumps([{"errorCount": 2, "warningCount": 5}, {"errorCount": 1, "warningCount": 0}])
        )
        self.assertEqual(s.count_eslint(self.d), 3)
        self.assertIsNone(s.count_eslint(self.d / "nope"))

    def test_ruff(self):
        (self.d / "ruff.json").write_text(json.dumps([{"code": "E501"}, {"code": "F401"}]))
        self.assertEqual(s.count_ruff(self.d), 2)

    def test_ruff_format(self):
        (self.d / "ruff-format.code").write_text("0\n")
        self.assertTrue(s.format_ok(self.d))
        (self.d / "ruff-format.code").write_text("1\n")
        self.assertFalse(s.format_ok(self.d))

    def test_ty(self):
        (self.d / "ty.txt").write_text(
            "app/a.py:1:2: error[x] 메시지\napp/b.py:3:4: warning[y] 메시지\nFound 2 diagnostics\n"
        )
        self.assertEqual(s.count_ty(self.d), 2)
        (self.d / "ty.txt").write_text("All checks passed!\n")
        self.assertEqual(s.count_ty(self.d), 0)

    def test_broken_json_is_unmeasured(self):
        (self.d / "ruff.json").write_text("not json")
        self.assertIsNone(s.count_ruff(self.d))
```

- [ ] **Step 2: 실패 확인** — `AttributeError: ... 'count_eslint'`

- [ ] **Step 3: 구현**

```python
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
    try:
        return (d / "ruff-format.code").read_text().strip() == "0"
    except OSError:
        return None


def count_ty(d: Path) -> int | None:
    try:
        text = (d / "ty.txt").read_text()
    except OSError:
        return None
    return len(re.findall(r"^\S+:\d+:\d+: (?:error|warning)\[", text, re.M))


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
    return any(n.startswith("frontend/") for n in names), any(n.startswith("backend/") for n in names)


def upsert_comment(repo: str, number: int, body: str) -> None:
    comments = gh_pages(f"repos/{repo}/issues/{number}/comments")
    mine = next((c for c in comments if MARKER in (c.get("body") or "")), None)
    if mine:
        gh("api", "-X", "PATCH", f"repos/{repo}/issues/comments/{mine['id']}", "-f", f"body={body}")
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
            frontend, backend, count_eslint(lint_dir) if frontend else None,
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
    except subprocess.CalledProcessError as e:  # 읽기 전용 토큰(Dependabot·포크)은 요약만 남긴다
        print(f"코멘트를 쓰지 못함(권한?): {sanitize(e.stderr or '', 200)}")


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except Exception as e:  # 비차단: 채점 실패가 PR을 막지 않는다
        print(f"채점 실패: {type(e).__name__}: {sanitize(str(e), 300)}")
    sys.exit(0)
```
- [ ] **Step 4: 통과 확인**

Run: `python3 scripts/test_pr_review_score.py` → 전부 OK
Run: `ruff check scripts/ && ruff format --check scripts/` — 이 레포의 ruff 설정은 `backend/`에만 있으므로 `backend/.venv/bin/ruff check --line-length 99 scripts/` 로 확인하고 지적은 수정한다.

- [ ] **Step 5: 커밋** — `git add scripts/ && git commit -m "ci(review): 린트 결과 파서와 GitHub I/O, 비차단 main"`

---

### Task 7: 워크플로

**Files:**
- Create: `.github/workflows/pr-review.yml`

- [ ] **Step 1: 워크플로 작성**

```yaml
name: PR Review

# PR 자동 점검 점수 (비차단). 설계: docs/superpowers/specs/2026-10-03-pr-review-scoring-design.md
# 점수는 PR 코멘트 1개와 잡 요약으로 보여 준다. 실패해도 PR을 막지 않는다 (필수 체크 아님).
# pull_request_target 은 쓰지 않는다 — 포크 PR 코드로 시크릿·쓰기 토큰을 쓰지 않기 위해.
on:
  pull_request:
    types: [opened, synchronize, edited, reopened]

permissions:
  contents: read
  pull-requests: write
  issues: write # PR 코멘트는 issues API

concurrency:
  group: pr-review-${{ github.event.pull_request.number }}
  cancel-in-progress: true

jobs:
  score:
    runs-on: ubuntu-latest
    env:
      GH_TOKEN: ${{ github.token }}
    steps:
      - uses: actions/checkout@v4
      - name: 채점 스크립트 자체 테스트
        run: python3 scripts/test_pr_review_score.py
      - id: areas
        run: python3 scripts/pr_review_score.py --areas
      - run: mkdir -p lint

      - if: steps.areas.outputs.frontend == 'true'
        uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - if: steps.areas.outputs.frontend == 'true'
        working-directory: frontend
        run: |
          npm ci
          npx eslint . --format json --output-file "$GITHUB_WORKSPACE/lint/eslint.json" || true

      - if: steps.areas.outputs.backend == 'true'
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      - if: steps.areas.outputs.backend == 'true'
        working-directory: backend
        run: |
          pip install uv
          uv venv && uv pip install -r requirements-dev.txt
          .venv/bin/ruff check --output-format json . > "$GITHUB_WORKSPACE/lint/ruff.json" || true
          .venv/bin/ruff format --check . > /dev/null 2>&1; echo $? > "$GITHUB_WORKSPACE/lint/ruff-format.code"
          .venv/bin/ty check --output-format concise app tests evals > "$GITHUB_WORKSPACE/lint/ty.txt" 2>&1 || true

      - name: 채점하고 코멘트 남기기
        run: python3 scripts/pr_review_score.py --lint-dir lint
```

- [ ] **Step 2: 문법 확인**

Run: `python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/pr-review.yml'))" 2>&1 || ruby -ryaml -e 'YAML.load_file(".github/workflows/pr-review.yml")'`
Expected: 오류 없음. (둘 다 없으면 push 후 Actions가 파싱한다.)

- [ ] **Step 3: 로컬에서 린트 산출물 형식 확인**

```bash
cd backend && mkdir -p /tmp/lint-try && \
  .venv/bin/ruff check --output-format json . > /tmp/lint-try/ruff.json; \
  .venv/bin/ty check --output-format concise app tests evals > /tmp/lint-try/ty.txt 2>&1; \
  python3 -c "
import sys; sys.path.insert(0,'../scripts')
import pr_review_score as s; from pathlib import Path
d=Path('/tmp/lint-try'); print(s.count_ruff(d), s.count_ty(d))"
```
Expected: `0 0` (현재 main은 ruff·ty 모두 깨끗)

- [ ] **Step 4: 커밋** — `git add .github/workflows/pr-review.yml && git commit -m "ci(review): PR Review 워크플로 (영역별 린트 + 채점, 비차단)"`

---

### Task 8: 검증과 PR

- [ ] **Step 1: 변이 시험** — 격리된 임시 사본/worktree에서 아래 순서로 확인한다.

1. `python3 scripts/test_pr_review_score.py`의 정상 통과를 먼저 기록한다.
2. 테스트 동반 경계 `30`을 `50`으로 바꾸는 등 채점 규칙 하나만 변이시키고 diff를 확인한다.
3. 같은 명령의 **전체 결과와 종료 코드**를 확인한다. 경계값 테스트 때문에 실패해야 하며, 의존성 누락 등 다른 실패는 변이를 잡았다는 증거가 아니다.
4. 자신이 만든 변이만 제거하고 같은 명령이 다시 통과하는지 확인한다. 기존 변경을 통째로 되돌리거나 `tail` 파이프의 종료 코드를 테스트 성공으로 사용하지 않는다.

- [ ] **Step 2: 충돌 검사·리뷰** — `scripts/check-conflicts.sh`, `reviewer` 서브에이전트(보안: 코멘트에 외부 입력이 무력화되는지, 워크플로 권한)

- [ ] **Step 3: push·PR** (사용자 확인 후) — 제목 `ci(review): PR 자동 점검 점수 (PR 1/2)`, 본문에 설계 문서 링크, 검증 항목, "AI 리뷰 블록이 아직 없어 'AI 리뷰 필요'로 표시되는 것이 정상" 명시

- [ ] **Step 4: 실환경 확인** — 이 PR에서 워크플로가 돌아 코멘트가 1개 생기는지, 푸시를 더 했을 때 같은 코멘트가 갱신되는지(`gh pr view <n> --comments`), 잡 요약이 보이는지 확인한다.

- [ ] **Step 5: 감점 시험** — 임시 브랜치에서 의도적으로 ruff 위반 1건(예: 미사용 import)과 `ty` 진단 1건을 넣은 draft PR을 열어 해당 항목 감점이 코멘트에 보이는지 확인하고 PR을 닫는다. Dependabot PR(예: #55)에서 워크플로가 실패 없이 끝나는지(코멘트는 건너뜀) 확인한다.

---

## 자체 점검 (spec 대조)

| spec | 담당 |
|---|---|
| §4.1 자동 6항목 + §4.1.2 분류 | Task 1, 2 |
| §4.1.1 린트·타입(절대 기준, 해당 없음 만점, 측정 못 함 환산) | Task 3, 6 |
| §4.3 판정·차단 이슈 | Task 4 |
| §5 블록 파싱·검증(합계·배점·6항목·섹션 경고) | Task 4 |
| §6 최신성(없음=형식 오류, 뒤처짐=경고) | Task 4, 6 |
| §6 코멘트 1개 갱신·잡 요약·읽기 전용 토큰 403 건너뜀·비차단 | Task 6, 7 |
| §6 보안(무력화·pull_request_target 금지) | Task 5, 7 |
| §9 테스트·변이 시험·실환경 | Task 1–6, 8 |
| §8.1의 PR 2(문서·reviewer·handoff·템플릿) | **이 계획 범위 밖 — PR 1 머지 후 별도 계획** |
