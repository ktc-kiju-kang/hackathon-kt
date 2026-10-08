---
name: add-endpoint
description: 기능에 API 엔드포인트를 계약부터 프론트 연동까지 추가 — docs/contracts, (필요 시) PostgreSQL 마이그레이션, FastAPI router·service·schema·테스트(TC ID), frontend features api.ts 타입·mock. 새 API나 백엔드-프론트 연결이 필요할 때 사용.
argument-hint: <feature> <METHOD> <path> <설명>
---
엔드포인트를 추가한다: $ARGUMENTS

0. **구현 원칙** — `/ponytail`(기본 full)을 적용한다: 기존 service·schema·패턴 재사용 → 표준 라이브러리 → 설치된 의존성 → 최소 구현. 검증·권한·계약·테스트는 줄이지 않는다.

1. **계약** — `docs/contracts/<feature>.md` (없으면 `docs/contracts/README.md` 템플릿으로 생성하고 목록에 추가)에 메서드·경로(`/api/<feature>/...`)·Request/Response JSON·에러·관련 REQ ID를 적는다. 사용자에게 보여주고 확인받는다. `docs/arch.md` "API" 표에도 한 줄.
2. **데이터 저장 위치** — 공개된 읽기 전용 데이터면 `backend/data/` 파일 + 메모리 로드. 사용자가 만드는 데이터면 DB:
   **DB** — `database/migrations/$(date +%Y%m%d%H%M)_<설명>.sql` 새 파일 (만든 시각 이름 — 번호 경쟁 없음) (PostgreSQL 문법, 규칙: `database/README.md`). 소유자 컬럼을 두고, 서버를 다시 켜면 자동 적용된다. 계약 문서와 `docs/arch.md` "데이터 모델"에도 적는다.
3. **backend** (`backend/app/`) — 기능 이름은 backend·frontend `features/`·계약·테스트·API 경로에서 모두 같게 쓴다.
   - `schemas/<feature>.py`: Pydantic 모델 (계약과 필드명·타입 일치, 문자열 길이 상한 `Field(max_length=...)`)
   - `services/<feature>.py`: 로직·DB 접근 (`with get_db() as db: db.execute("... where owner_id = ?", (...))`). **행 접근 권한 체크를 service에서** 한다 (남의 것이면 404)
   - `routers/<feature>.py`: `router = APIRouter(prefix="/<feature>", tags=["<feature>"])`, 핸들러는 service 호출만, `response_model` 지정. `main.py`는 자동 등록이라 고치지 않는다.
   - `tests/test_<feature>.py`: AC마다 테스트 — **정상 + 오류(422 등) + 권한 경계(남의 자료 404, 저장값 불변)**. 테스트 이름에 TC ID (`test_tc_01_1_...`). conftest가 테스트마다 새 PostgreSQL schema를 준다.
4. **frontend** — `frontend/src/features/<feature>/api.ts`
   - 계약과 같은 TS 타입, `@/lib/api-client`의 `request`로 호출하는 함수
   - `isMock`이면 계약 형태의 mock 반환 (`features/health/api.ts` 패턴)
5. **LLM이 결과를 만드는 API면** — `.claude/rules/agent.md`의 "LLM이 결과 객체를 만드는 API" (`StageRunner`·`stream_stages`, mock 결과, 호출 상한, 입력 태그·크기 상한).
6. **검증** — backend: ruff + ty + pytest, frontend: lint + test + build 모두 통과. `fastapi dev`로 띄워 `/api/docs`에서 한 번 호출해 본다.
7. **근거** — `docs/e2e-test.md`의 해당 TC에 실행 명령(예: `pytest tests/test_<feature>.py -k tc_01_3`)과 실제 결과를 채운다.
8. 결과로 계약 요약, 변경 파일, 컴포넌트에서 호출하는 예시 한 줄을 보여준다.
