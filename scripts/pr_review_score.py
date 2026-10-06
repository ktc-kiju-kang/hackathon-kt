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
