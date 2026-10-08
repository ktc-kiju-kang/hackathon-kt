# API 계약

> 기능 간·프론트-백엔드 간 경계가 되는 API/타입을 **기능별 파일** `docs/contracts/<feature>.md`로 정의한다.
> 구현보다 계약이 먼저다. 다른 기능이 쓰는 계약을 바꾸면 그 기능 담당자에게 PR 리뷰를 요청한다.

## 공통
- Base: 로컬 `http://localhost:8000`
- 모든 경로는 `/api/<feature>/...` 접두사
- 자동 문서: `/api/docs` (FastAPI). 구현 스키마는 `backend/app/schemas/<feature>.py`, 프론트 타입은 `frontend/src/features/<feature>/api.ts`
- 에러 응답: `{ "detail": string }` (FastAPI 기본)
- 시간은 ISO 8601 문자열(UTC), ID는 문자열

## 템플릿 (`docs/contracts/<feature>.md`)
```markdown
# <feature>
- 담당: @github-id · 이슈: #번호
- 사용처: (이 API를 호출하는 기능/화면)
- DB: (사용 테이블·마이그레이션 파일, 없으면 생략)

## GET /api/<feature>/...  — v1
Request:  ...
Response 200: { ... }
Errors: 404 { "detail": "..." }

## 변경 이력
| 날짜 | 변경 | 작성자 |
```

## 목록
- [health](health.md) — 서버 상태 확인
- [dashboard](dashboard.md) — 개발/배포 현황판 (서버·DB·시험·REQ·GitHub, #99)
- [chat](chat.md) — AI 에이전트 대화 (SSE 스트리밍)
- [stages](stages.md) — LLM 단계형 생성 공통 스트림 형식
