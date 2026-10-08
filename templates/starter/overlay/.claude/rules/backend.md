---
paths:
  - "backend/**"
---

# backend 코드 규칙

> `backend/**` 파일을 다룰 때 자동으로 로드된다. AI 에이전트·LLM은 `.claude/rules/agent.md`, DB 규칙은 `database/README.md`.

- 기능 = `routers/<feature>.py` + `services/<feature>.py` + `schemas/<feature>.py`.
  - `router = APIRouter(prefix="/<feature>", tags=["<feature>"])`를 정의하면 자동 등록 → `/api/<feature>/...`
  - router는 얇게(검증·응답), 로직·DB 접근은 service에. `response_model` 항상 지정.
- DB는 `app.core.db.get_db()`로 service에서만 접근 (SQLite). 설정·비밀값은 `app/core/config.py`의 `Settings`로만 읽는다.
- DB 사용 예 (service):
  ```python
  from app.core.db import get_db
  with get_db() as db:  # 블록이 끝나면 commit, 예외면 rollback
      rows = db.execute("select * from items where owner_id = ?", (owner_id,)).fetchall()
  return [dict(r) for r in rows]
  ```
  - **권한 체크(누가 어떤 행에 접근 가능한지)는 service 코드에서** 한다. 남의 행이면 404(존재 여부도 숨김). 예: `services/chat.py`의 `_owned`.
  - 값은 항상 `?`·`:name` 자리표시자로. f-string으로 SQL을 만들지 않는다.
- 기능마다 `tests/test_<feature>.py`에 **정상 + 오류 + 권한 경계** 테스트. 테스트 이름 또는 docstring에 TC ID를 적는다 (예: `def test_tc_01_3_other_users_item_is_hidden`). `docs/e2e-test.md`가 이 테스트를 근거로 가리킨다.
  - `conftest.py`가 테스트마다 새 SQLite 파일(`tmp_path`)을 주고 LLM 키를 비운다 → 로컬 `.env`와 무관하게 통과한다.
- `schema_migrations` 테이블은 마이그레이션 전용. 기능에서 읽거나 쓰지 않는다.
- 공개된 읽기 전용 정적 데이터는 DB 대신 `backend/data/<이름>/`에 두고 처음 호출 때 메모리에 읽는다 (`lru_cache`). 출처·라이선스를 README에 적는다.
- ruff `target-version`이 py311이다 → 3.12 문법(`def f[T](...)`, `type X = ...`)을 쓰지 않는다. 제네릭은 `TypeVar`.
- 쿼리 파라미터에 `Literal[0, 1]` 같은 정수 Literal을 쓰지 않는다 (문자열 `"1"`이 422). `int` + `Query(ge=0, le=1)`.
- 테스트의 LLM 고정: `conftest.py`는 키를 비우고 `app.agent.loop.get_provider`만 mock으로 바꾼다. 단계형 생성 API는 `use_provider(provider)` fixture로 고정한다 (라우터가 `Depends(llm_provider)`로 받는 provider를 override).

## 파이썬 스타일
- [PEP 8](https://peps.python.org/pep-0008/). 형식·이름·import 순서는 ruff, 타입은 ty가 강제한다.
- 줄 길이 99자, 주석·독스트링은 한국어, 주석은 이유(왜)를 쓴다. `# noqa`·`# ty: ignore`는 이유를 적을 때만.

로컬 확인: `cd backend && .venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/ty check app tests && .venv/bin/pytest`
