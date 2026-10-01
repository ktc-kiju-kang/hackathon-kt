# 0004. 배포 파이프라인: GitHub Actions가 지휘

- 상태: 채택
- 날짜: 2026-10-01

## 결정
main CI 통과 시 `.github/workflows/deploy.yml`이 **마이그레이션(Supabase) → backend(Render Deploy Hook) → frontend(Vercel CLI) → 스모크 테스트** 순으로 배포한다. Vercel(main)·Render의 플랫폼 자동배포는 끈다. Vercel PR 프리뷰는 유지.

## 이유
- 배포 순서 보장: DB → API → 화면. API가 뜬 것(health `version` = 커밋 SHA)을 확인한 뒤 프론트를 바꾼다.
- 배포 결과·실패 원인이 GitHub 한 곳에 남고, 수동 재배포 버튼이 생긴다.
- 프론트 빌드 시 API URL이 비어 있으면 배포를 막아 "조용한 mock" 사고를 방지.

## 트레이드오프
- 시크릿 5개 관리 필요 (`RENDER_DEPLOY_HOOK_URL`, `VERCEL_*`, `SUPABASE_DB_URL`).
- 마이그레이션이 backend보다 먼저 적용 → 마이그레이션은 이전 코드와 호환되게 작성해야 한다.
- 롤백 자동화 없음. 문제 시 revert PR을 머지하면 같은 파이프라인으로 되돌린다 (스키마는 되돌리지 않음).
