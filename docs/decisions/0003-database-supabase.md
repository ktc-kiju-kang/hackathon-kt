# 0003. DB: Supabase (FastAPI 경유)

- 상태: 채택
- 날짜: 2026-10-01

## 결정
Supabase Postgres를 팀이 공유하는 클라우드 프로젝트 하나로 사용. **백엔드만** `service_role` 키로 접근하고, 프론트는 FastAPI만 호출한다. 스키마는 `database/migrations/*.sql`로 관리.

## 이유
- 계약(`docs/contracts/`)과 데이터 접근 로직이 FastAPI 한 곳에 모인다.
- 비밀 키가 백엔드(Render)에만 존재한다.

## 트레이드오프
- Supabase Auth·Realtime을 프론트에서 바로 쓰는 이점은 포기 (필요 시 별도 ADR).
- 공유 DB라 마이그레이션 충돌·파괴적 변경에 주의 (`database/README.md`).
- Docker 기반 로컬 Supabase는 쓰지 않는다 (해커톤 셋업 비용).
