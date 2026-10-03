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
