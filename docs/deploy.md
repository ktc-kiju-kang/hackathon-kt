# 배포 & 환경변수

> 요약은 `CLAUDE.md`, 단계별 완료 정의는 [SDLC](SDLC.md), 상태 확인은 `/deploy-status`.
> 아래 자동 동작은 [deploy.yml](../.github/workflows/deploy.yml)·[migrate.sh](../scripts/migrate.sh)·[smoke.sh](../scripts/smoke.sh)를 기준으로 2026-10-06 대조했다.

**main 머지 → CI 통과 → `.github/workflows/deploy.yml`이 순서대로 배포한다.** 플랫폼 자체 자동배포(main)는 끄는 것이 운영 규칙이다. 대시보드 설정은 워크플로 파일만으로 확인할 수 없다.

| 단계 | 대상 | 방법 | 실패 시 |
|---|---|---|---|
| 1. migrate | Supabase | `scripts/migrate.sh` (미적용 파일만, `schema_migrations` 기록) | 실패 파일의 트랜잭션 롤백·이후 단계 중단. 앞서 성공한 파일은 유지 |
| 2. backend | Render | Deploy Hook → `/api/health`의 `version`이 머지 커밋 SHA가 될 때까지 대기 | frontend 배포 안 함 |
| 3. frontend | Vercel | `vercel build/deploy --prod` (API URL 비어 있으면 중단) | 배포 전 실패라면 기존 frontend 유지. 배포 명령 도중 실패는 실제 상태 확인 필요 |
| 4. smoke | 전체 | `scripts/smoke.sh <sha>` (health·version·**db**·홈 HTTP 200·CORS) | Actions 실행 실패로 표시. 이미 배포된 서비스는 자동 복구되지 않음 |

- PR 프리뷰: Vercel이 PR마다 자동 생성 (main만 Actions가 배포). 백엔드 프리뷰는 없음.
- 수동 재배포: **사용자 확인 후** Actions → Deploy → Run workflow, 또는 `gh workflow run deploy.yml --ref main`. 수동 실행은 CI 성공을 자동 전제하지 않으므로 대상 main의 CI·변경 내용을 먼저 확인한다.
- 배포용 GitHub Secrets: `RENDER_DEPLOY_HOOK_URL`, `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`, `SUPABASE_DB_URL`(없으면 마이그레이션 건너뜀). **`production` Environment secrets에 넣고 main만 접근하도록 설정한다.** 실제 Environment 보호 설정은 관리자가 확인해야 한다.
- 실행 제한: 자동 Deploy는 같은 저장소의 main push CI 성공에서만 시작하고, 수동 실행은 main에서만 허용한다. fork PR·다른 브랜치의 수동 실행은 잡 조건으로 차단한다.
- **마이그레이션 예외**: `SUPABASE_DB_URL`이 없으면 경고만 출력하고 성공 종료하므로 backend 배포는 계속된다. migrate 잡 성공만으로 DB 변경 적용을 증명할 수 없다. DB 변경 PR은 해당 실행의 적용/미적용 로그까지 확인한다.
- **상태 확인 범위**: `db: ok`는 연결·키 확인이며, 모든 테이블의 스키마·업무 쿼리·백업 복원 검증은 아니다. smoke는 홈 HTTP 200을 확인할 뿐 `/trends` → `/radar` → `/product`를 조작하지 않는다.

| 환경변수 위치 | 내용 |
|---|---|
| Vercel 프로젝트 (Config 타입) | `NEXT_PUBLIC_API_BASE_URL` = Render URL |
| Render 대시보드 | `CORS_*`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`(**`service_role` 또는 `sb_secret_` 키** — anon/publishable이면 쓰기가 RLS에 막힘, health `db: error`로 표시). LLM은 `ANTHROPIC_API_KEY` 또는 `GEMINI_API_KEY`, OpenAI 호환은 `LLM_PROVIDER=openai`·`LLM_BASE_URL`·`LLM_MODEL`·`LLM_API_KEY`. 필요 시 `LLM_EFFORT`·`CHAT_DAILY_LIMIT` (`render.yaml`은 참고용 — Blueprint 미연결 시 대시보드가 실제 값) |

- 전체 키 목록은 루트 `.env.example`. 로컬 값은 `frontend/.env.local`, `backend/.env` (커밋 금지).
- `NEXT_PUBLIC_*`는 브라우저 번들에 노출된다. 비밀값 금지. **`SUPABASE_SERVICE_ROLE_KEY`는 백엔드에만.**
- CORS: `https://hackathon-kt.vercel.app`, `localhost:3000`, Vercel 프리뷰(`hackathon-*-ktc-kiju-kang.vercel.app`) 허용.
- Render free는 15분 미사용 시 잠든다(첫 요청 ~1분). 데모 직전에 `/api/health`를 호출해 깨운다.

## 배포 전후 확인

1. **배포 전**: PR의 완료 조건·변경 영역 검증·요청한 리뷰 답변을 확인한다. 마이그레이션은 [DB 규칙](../database/README.md)에 따라 번호·이전 코드 호환·적용 순서를 확인한다. 환경변수는 이름·필요 위치만 기록하고 값을 남기지 않는다.
2. **대상 고정**: 자동 실행은 연결된 main CI의 `head_sha`, 수동 실행은 해당 main SHA를 기록한다. 배포 중 main이 바뀌더라도 진행 중인 실행의 기대 SHA를 임의로 바꾸지 않는다.
3. **배포 후**: Deploy URL·4개 잡 결과·migrate 경고/적용 로그, health `status`·`version`·`db`·`llm`, 변경 기능의 수동 확인을 PR 또는 작업 기록에 남긴다. health 전체 원문 대신 필요한 필드만 기록해 `client_ip`를 공개하지 않는다.
4. **인수 판정**: 스모크 성공만으로 기능 완료를 선언하지 않는다. UI·생성·내보내기는 [리허설 기준](DEMO.md#리허설-통과-기준)에 따라 확인하고, 실패하면 후속 이슈와 담당자를 연결한다.

## 실패 시 판단과 되돌리기

| 실패 위치 | 남아 있을 수 있는 상태 | 대응 |
|---|---|---|
| migrate | 기존 앱 + 앞서 적용된 일부 새 스키마 | 실패 로그와 적용 여부 확인. 미적용 실패 파일은 수정 PR로 재시도할 수 있고, 이미 적용된 파일의 변경은 새 마이그레이션으로 처리. 적용 기록 직접 수정 금지 |
| backend 대기 | 새 스키마 + 이전 또는 새 backend, 기존 frontend | health SHA·Render Events 확인. 타임아웃은 실제 배포 실패와 동일하지 않음 |
| frontend | 새 backend + 기존 또는 새 frontend | Vercel 실제 배포 상태와 API 호환성을 먼저 확인. backend는 자동으로 돌아가지 않음 |
| smoke | 새 앱이 이미 운영 중일 수 있음 | 실제 사용자 영향 판단 후 수정 PR 또는 revert PR. Actions 실패 표시가 서비스 복구를 뜻하지 않음 |

**코드 회귀의 기본 복구 경로**

1. 마지막 정상 실행·문제 PR·현재 health SHA·영향을 기록하고 추가 변경을 멈춘다. 설정 오류인지 코드 회귀인지 구분해 불필요한 revert를 피한다.
2. 코드 회귀라면 작업 브랜치에서 대상 변경의 **revert PR**을 만든다. 최신 DB 스키마와 이전 앱의 호환성을 확인하고, PR에는 되돌릴 범위와 데이터 영향·남는 변경을 적는다. PR 생성은 사용자 확인 후, 머지는 사람이 한다.
3. revert PR의 CI → 머지 → Deploy를 확인한다. health `version`은 **새 revert 배포 SHA**와 일치해야 하며, 문제가 났던 기능을 다시 확인해야 복구 완료다.
4. 설정·플랫폼 문제라면 권한 있는 담당자가 원인을 해소한 뒤 승인받아 main 재배포한다. 수동 실행은 현재 main을 배포하는 동작이지 과거 버전을 선택하는 롤백이 아니다.

**DB 주의**: 코드 revert로 스키마·데이터가 복원되지 않는다. 공유 DB 직접 SQL·수동 마이그레이션 실행은 하지 않는다. 특히 `scripts/migrate.sh --dry-run`도 시작할 때 적용 기록 테이블 생성·RLS 설정을 실행하므로 공유 DB의 읽기 전용 점검으로 사용하면 안 된다. 복구는 마이그레이션 파일과 배포 파이프라인으로 처리한다.

정기 상태 감시·외부 알림 채널·자동 롤백·DB 복원 리허설·RTO/RPO는 현재 검증된 운영 장치가 아니다. 복구 기록에는 발견/완료 시각·영향·원인과 가설·조치·재확인·재발 방지 담당을 남긴다.
