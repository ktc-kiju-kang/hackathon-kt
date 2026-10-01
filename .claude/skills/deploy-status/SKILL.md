---
name: deploy-status
description: 배포 상태 확인 — Deploy 워크플로(마이그레이션→backend→frontend→스모크) 결과와 운영 서비스 상태 점검, 실패 원인 안내. 배포 확인, 배포 실패, 데모 직전 점검 시 사용.
---
1. 파이프라인: `gh run list --workflow deploy.yml --limit 5` 와 `gh run list --workflow ci.yml --branch main --limit 3`.
   - 최신 main 커밋(`git rev-parse origin/main`)에 대한 Deploy가 성공했는지 확인한다.
   - 실패했으면 `gh run view <id> --log-failed`로 실패 단계와 원인을 요약한다:
     - migrate: SQL 오류 → 새 마이그레이션 파일로 수정 / `SUPABASE_DB_URL` 연결 실패 → Session pooler URL인지 확인
     - backend: Deploy Hook secret 없음 / 15분 내 새 version 미반영 → Render 대시보드 로그 확인
     - frontend: Vercel secret 없음 / `NEXT_PUBLIC_API_BASE_URL` 비어 있음 / 빌드 실패 / deploy 단계 "Project not found" → `VERCEL_ORG_ID`가 Team ID(`team_…`)가 아님
     - smoke: 아래 3번 결과 참고. `DB 연결 이상: error` → Render의 `SUPABASE_URL`/`SUPABASE_SERVICE_ROLE_KEY` 오타·만료 (Render 로그에 `db health check failed`) 또는 **anon/publishable 키를 넣음** (로그 `is not a service_role key`, 증상: 대화 생성 500 `row-level security`), `unconfigured` → Render에 두 값이 없음
2. 수동 재배포가 필요하면 사용자 확인 후 `gh workflow run deploy.yml`.
3. 운영 상태: `scripts/smoke.sh $(git rev-parse origin/main)` — API health·version(=main SHA)·db(Supabase)·화면 200·CORS.
   - version 불일치는 backend가 아직 이전 커밋이라는 뜻. Render free는 잠들어 있으면 첫 응답 ~1분.
4. 결과를 단계별 정상/이상으로 요약한다.
