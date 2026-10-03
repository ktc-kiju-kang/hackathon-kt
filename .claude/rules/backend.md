---
paths:
  - "backend/**"
---

# backend 코드 규칙

> `backend/**` 파일을 다룰 때 자동으로 로드된다. AI 에이전트·LLM·구조화 생성은 `.claude/rules/agent.md`.

- 기능 = `routers/<feature>.py` + `services/<feature>.py` + `schemas/<feature>.py`.
  - `router = APIRouter(prefix="/<feature>", tags=["<feature>"])`를 정의하면 자동 등록 → `/api/<feature>/...`
  - router는 얇게(검증·응답), 로직·DB 접근은 service에. `response_model` 항상 지정.
- DB는 `app.core.db.get_supabase()`로 service에서만 접근. 설정·비밀값은 `app/core/config.py`의 `Settings`로만 읽는다.
- DB 사용 예 (service):
  ```python
  from app.core.db import get_supabase
  rows = get_supabase().table("items").select("*").eq("owner", uid).execute().data
  ```
  `service_role` 키라 RLS를 우회한다 → **권한 체크(누가 어떤 행에 접근 가능한지)는 service 코드에서** 한다.
- 기능마다 `tests/test_<feature>.py`에 최소 1개 테스트. DB가 필요한 테스트는 service 함수를 monkeypatch해 DB 없이 돌게 한다 (CI에는 DB 없음).
  - 로컬 `backend/.env`에 실제 Supabase 키가 있으면 테스트가 실제 DB에 붙는다. 테스트는 `monkeypatch.setattr(settings, ...)`로 설정을 고정해 **로컬 .env와 무관하게** 통과해야 한다.
- `schema_migrations` 테이블은 배포 파이프라인 전용. 기능에서 읽거나 쓰지 않는다.
- **공개된 읽기 전용 정적 데이터는 DB 대신 `backend/data/`에** 두고 처음 호출 때 메모리에 읽는다 (`lru_cache`). 출처·라이선스를 `README.md`에 적는다. CSV는 `csv` 모듈로 문자열 그대로 읽는다 (pandas는 나미비아 코드 `NA`를 결측값으로 바꾼다). 사용자가 만드는 데이터는 DB(마이그레이션)로.
- ruff `target-version`이 py311이다 → 3.12 문법(`def f[T](...)`, `type X = ...`)을 쓰지 않는다. 제네릭은 `TypeVar`.
- 쿼리 파라미터에 `Literal[0, 1]` 같은 정수 Literal을 쓰지 않는다 (문자열 `"1"`이 422). `int` + `Query(ge=0, le=1)`.
- 테스트의 LLM 고정: `conftest.py`는 키를 비우고 `app.agent.loop.get_provider`만 mock으로 바꾼다. **radar·product(단계 파이프라인)는 `use_provider(provider)` fixture**(`conftest.py`)로 고정한다 — 라우터가 `Depends(llm_provider)`로 받는 provider를 `app.dependency_overrides`로 바꾸므로 모듈 monkeypatch가 필요 없다. `mock_llm`은 mock 고정이다 (로컬 `.env`의 `LLM_PROVIDER`와 무관하게). 서비스 모듈에 `get_provider`를 import해 직접 부르지 않는다 — 라우터가 `Annotated[LLMProvider, Depends(llm_provider)]`로 받아 서비스 진입 함수의 `provider` 인자로 넘긴다.

## 파이썬 스타일: PEP 8을 따른다

기준은 [PEP 8](https://peps.python.org/pep-0008/). 형식·이름·import 순서는 **ruff가 자동으로 강제**하고(CI), 아래 "사람이 판단"은 리뷰에서 본다. 타입은 `ty`가 CI에서 막는다 (`# ty: ignore[규칙]`은 이유 주석과 함께 최소한으로).

| PEP 8 항목 | 강제 | ruff 규칙 |
|---|---|---|
| 들여쓰기 4칸·공백·빈 줄·줄 끝 공백 | 자동 | `E`, `W`, `ruff format` |
| import 맨 위, 표준 → 서드파티 → 앱 순서, 한 줄에 하나 | 자동 | `I` |
| 이름: 함수·변수 `snake_case`, 클래스 `CapWords`, 상수 `UPPER_CASE`, 예외 이름은 `Error`로 끝남 | 자동 | `N` |
| 일관된 `return` (값을 반환하는 함수는 모든 경로에서 반환) | 자동 | `RET` |
| 미사용 import·변수, `==  None` 비교, 예외 처리 함정 | 자동 | `F`, `E`, `B` |
| 줄 길이·독스트링·주석 길이 | 자동 | `E501`, `W505` (99자) |
| 주석은 코드와 모순되지 않게, 이유(왜)를 쓴다 | **사람이 판단** | — |
| 이름은 뜻이 드러나게 (`l`·`O`·`I` 한 글자 이름 금지는 자동) | **사람이 판단** | `E741` 일부 |
| `is None` 비교, `isinstance`, 빈 시퀀스의 참거짓 | 일부 자동 | `E711`, `E712` |

**PEP 8과 다르게 가는 부분** (의도된 것):
- 줄 길이 **99자**. PEP 8의 79자는 한글 주석·타입 힌트가 많은 이 코드에 비해 좁다 (PEP 8도 팀이 합의하면 99자까지 허용). 독스트링·주석도 99자.
- 주석·독스트링은 **한국어**. (PEP 8 "주석은 영어" 권고는 국제 코드베이스 기준이라 따르지 않는다.)
- 독스트링 형식(PEP 257, ruff `D`)은 강제하지 않는다. 모듈·공개 함수에 한 줄 요약이면 충분하다.

로컬 확인은 `cd backend && .venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/ty check app tests evals`. 새 코드는 포맷터가 고치는 대로 맞추고, 규칙을 끄는 `# noqa`는 이유를 적을 때만 쓴다.
