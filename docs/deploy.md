# 배포 & 환경변수

> 요약은 `CLAUDE.md`. 장애·되돌리기는 `docs/SDLC.md`, 상태 확인은 `/deploy-status`.

**main 머지 → CI 통과 → `.github/workflows/deploy.yml`이 순서대로 배포한다.** 플랫폼 자체 자동배포(main)는 끈다.

| 단계 | 대상 | 방법 | 실패 시 |
|---|---|---|---|
| 1. migrate | Supabase | `scripts/migrate.sh` (미적용 파일만, `schema_migrations` 기록) | 이후 단계 중단, 해당 파일 롤백 |
| 2. backend | Render | Deploy Hook → `/api/health`의 `version`이 머지 커밋 SHA가 될 때까지 대기 | frontend 배포 안 함 |
| 3. frontend | Vercel | `vercel build/deploy --prod` (API URL 비어 있으면 중단) | 이전 버전 유지 |
| 4. smoke | 전체 | `scripts/smoke.sh <sha>` (health·version·**db**·화면·CORS) | 실패 알림 |

- PR 프리뷰: Vercel이 PR마다 자동 생성 (main만 Actions가 배포). 백엔드 프리뷰는 없음.
- 수동 재배포: Actions → Deploy → Run workflow (`gh workflow run deploy.yml`). 실패 원인 확인은 `/deploy-status`.
- 배포용 GitHub Secrets: `RENDER_DEPLOY_HOOK_URL`, `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`, `SUPABASE_DB_URL`(없으면 마이그레이션 건너뜀). **`production` Environment secrets에 넣는다** (보호 브랜치 main에서만 접근 가능).
- 보안: Deploy는 main push로 돈 CI에서만 실행된다 (fork PR·다른 브랜치 수동 실행 차단).

| 환경변수 위치 | 내용 |
|---|---|
| Vercel 프로젝트 (Config 타입) | `NEXT_PUBLIC_API_BASE_URL` = Render URL |
| Render 대시보드 | `CORS_*`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`(**`service_role` 또는 `sb_secret_` 키** — anon/publishable이면 쓰기가 RLS에 막힘, health `db: error`로 표시), `ANTHROPIC_API_KEY` 또는 `GEMINI_API_KEY`, (선택) `LLM_PROVIDER`·`LLM_MODEL`·`LLM_EFFORT` (`render.yaml`은 참고용 — Blueprint 미연결 시 대시보드가 실제 값) |

- 전체 키 목록은 루트 `.env.example`. 로컬 값은 `frontend/.env.local`, `backend/.env` (커밋 금지).
- `NEXT_PUBLIC_*`는 브라우저 번들에 노출된다. 비밀값 금지. **`SUPABASE_SERVICE_ROLE_KEY`는 백엔드에만.**
- CORS: `https://hackathon-kt.vercel.app`, `localhost:3000`, Vercel 프리뷰(`hackathon-*-ktc-kiju-kang.vercel.app`) 허용.
- Render free는 15분 미사용 시 잠든다(첫 요청 ~1분). 데모 직전에 `/api/health`를 호출해 깨운다.
