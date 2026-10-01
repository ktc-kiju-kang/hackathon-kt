---
name: add-endpoint
description: 기능에 API 엔드포인트를 계약부터 프론트 연동까지 추가 — docs/contracts, (필요 시) DB 마이그레이션, FastAPI router·service·schema·테스트, frontend features api.ts 타입·mock. 새 API나 백엔드-프론트 연결이 필요할 때 사용.
argument-hint: <feature> <METHOD> <path> <설명>
---
엔드포인트를 추가한다: $ARGUMENTS

1. **계약** — `docs/contracts/<feature>.md` (없으면 `docs/contracts/README.md` 템플릿으로 생성하고 목록에 추가)에 메서드·경로(`/api/<feature>/...`)·Request/Response JSON·에러·변경 이력을 적는다. 사용자에게 보여주고 확인받는다.
   - 다른 기능 담당자가 이 API를 쓰거나 남의 계약을 바꾸는 경우, 계약만 먼저 작은 PR로 올리자고 제안한다.
2. **DB (필요 시)** — `database/migrations/NNNN_<설명>.sql` 새 파일 (규칙: `database/README.md` — RLS 켜기, 기본 컬럼, 번호는 머지 직전 확정). 계약 문서의 "DB" 항목에도 적는다. **공유 DB에는 직접 적용하지 않는다** — main 머지 시 배포 파이프라인이 자동 적용. 이전 버전 backend와 호환되게 쓰고, Docker Postgres로 로컬 검증 (`database/README.md`).
3. **backend** (`backend/app/`)
   - `schemas/<feature>.py`: Pydantic 모델 (계약과 필드명·타입 일치)
   - `services/<feature>.py`: 로직·DB 접근 (`from app.db import get_supabase`)
   - `routers/<feature>.py`: `router = APIRouter(prefix="/<feature>", tags=["<feature>"])`, 핸들러는 service 호출만, `response_model` 지정. `main.py`는 자동 등록이라 고치지 않는다.
   - `tests/test_<feature>.py`: 정상 + 주요 에러 케이스. DB 쓰는 service는 `monkeypatch`로 대체해 DB 없이 통과하게 한다.
4. **frontend** — `frontend/src/features/<feature>/api.ts`
   - 계약과 같은 TS 타입, `@/lib/api-client`의 `request`로 호출하는 함수
   - `isMock`이면 계약 형태의 mock 반환 (`features/health/api.ts` 패턴)
5. **검증** — backend: ruff + pytest, frontend: lint + build 모두 통과.
6. 결과로 계약 요약, 변경 파일, 컴포넌트에서 호출하는 예시 한 줄을 보여준다.
