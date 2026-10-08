"""E2E 시험: `make e2e`가 띄운 격리 로컬 배포(새 DB·mock LLM)에 HTTP로 붙는다.

- 주소: E2E_API_URL, E2E_WEB_URL (기본 make serve 주소)
- 서버가 없으면 skip. make e2e는 E2E_REQUIRED=1로 실행해 실패로 본다.
- 테스트 이름에 TC ID를 넣으면 docs/e2e-test.md에 결과가 자동 기록된다: def test_tc_01_2_...
- 데이터는 합성 데이터만, 테스트마다 새 X-Client-Id(사용자)를 만든다.
"""

import json
import os
import uuid
from collections.abc import Iterator

import httpx
import pytest

API = os.environ.get("E2E_API_URL", "http://localhost:8000")
WEB = os.environ.get("E2E_WEB_URL", "http://localhost:3000")


def _up(url: str) -> bool:
    try:
        return httpx.get(url, timeout=3).status_code < 500
    except httpx.HTTPError:
        return False


@pytest.fixture(scope="session")
def api() -> Iterator[httpx.Client]:
    if not _up(f"{API}/api/health"):
        msg = f"서버 없음: {API} (make serve 또는 make e2e)"
        if os.environ.get("E2E_REQUIRED") == "1":
            pytest.fail(msg)
        pytest.skip(msg)
    with httpx.Client(base_url=API, timeout=60) as client:
        yield client


@pytest.fixture(scope="session")
def web() -> Iterator[httpx.Client]:
    if not _up(WEB):
        msg = f"화면 서버 없음: {WEB}"
        if os.environ.get("E2E_REQUIRED") == "1":
            pytest.fail(msg)
        pytest.skip(msg)
    with httpx.Client(base_url=WEB, timeout=30) as client:
        yield client


@pytest.fixture
def user() -> dict[str, str]:
    """새 사용자 (로그인 없는 소유자 식별 헤더)."""
    return {"X-Client-Id": f"e2e-{uuid.uuid4()}"}


@pytest.fixture
def other_user() -> dict[str, str]:
    return {"X-Client-Id": f"e2e-other-{uuid.uuid4()}"}


def read_sse(res: httpx.Response) -> list[tuple[str, dict]]:
    """SSE 응답을 (event, data) 목록으로."""
    events, event = [], "message"
    for line in res.iter_lines():
        if line.startswith("event:"):
            event = line[6:].strip()
        elif line.startswith("data:"):
            events.append((event, json.loads(line[5:].strip())))
    return events
