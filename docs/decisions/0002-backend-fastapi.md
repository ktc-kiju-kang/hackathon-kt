# 0002. 백엔드: FastAPI

- 상태: 채택
- 날짜: 2026-10-01
- 관련: [0007](0007-folder-structure.md) — 폴더 구조(기능 폴더 `features/<feature>/`)가 이동 완료되면 아래 "routers/services/schemas 계층" 표기를 대체한다.

## 배경
AI/데이터 연동 가능성이 높고, 프론트와 API 계약을 빠르게 공유해야 한다.

## 결정
`backend/`에 FastAPI + Pydantic을 사용한다. 구조는 routers/services/schemas 계층에 기능별 파일. 의존성은 `requirements*.txt` + venv, 린트/포맷은 ruff, 테스트는 pytest.

## 결과 / 트레이드오프
- `/api/docs`에서 OpenAPI 문서가 자동 생성 → 프론트가 계약 확인 용이.
- 프론트(TS)와 타입 공유는 수동. 필요 시 OpenAPI → TS 타입 생성 도입 검토.
- 배포는 Render (`render.yaml`).
