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
