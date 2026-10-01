---
name: add-endpoint
description: API 엔드포인트를 계약부터 프론트 연동까지 추가 — CONTRACTS.md, FastAPI 라우터·스키마·테스트, web client 타입·mock. 새 API나 기능의 백엔드-프론트 연결이 필요할 때 사용.
argument-hint: <METHOD> <path> <설명>
---
엔드포인트를 추가한다: $ARGUMENTS

1. **계약** — `docs/CONTRACTS.md` "API" 섹션에 기존 형식대로 추가한다: 메서드·경로(`/api/...`), owner/consumer, Request/Response JSON, 에러. 변경 이력 표에 한 줄 추가. 사용자에게 계약을 보여주고 확인받는다.
   - 다른 멤버가 consumer면 계약만 먼저 작은 PR로 올리는 것을 제안한다.
2. **api** (`api/`)
   - `app/schemas.py`에 요청/응답 Pydantic 모델 (계약과 필드명·타입 일치)
   - `app/routers/<도메인>.py`에 라우터 (`response_model` 지정). 새 파일이면 `app/main.py`에 `app.include_router(<mod>.router, prefix="/api", tags=["<도메인>"])`
   - `tests/test_<도메인>.py`에 정상 케이스 + 주요 에러 케이스 테스트
3. **web** (`web/src/api/client.ts`)
   - 계약과 같은 TS 타입 추가
   - `api` 객체에 함수 추가. `BASE_URL`이 비어 있을 때 쓸 mock 응답도 둔다 (기존 `health` 패턴)
4. **검증** — api: ruff + pytest, web: lint + build 모두 통과.
5. 결과로 계약 요약, 변경 파일, 프론트에서 호출하는 예시 한 줄을 보여준다.
