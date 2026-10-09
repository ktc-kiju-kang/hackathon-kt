# 본선 시작 키트

> 10/14 주제 공개 → 10/15 00:00 개발 마감. 배정받은 팀 레포에 **첫 1시간 안에** 개발 환경·작업 규칙·제출 문서 뼈대를 깔기 위한 키트다.
> 결정: **로컬 우선** — 외부 서비스(Vercel·Render·Supabase) 없이 PC에서 실행하고 시험한다 (2026-10-08 팀 결정).
> 실행은 docker compose, DB는 PostgreSQL(테스트·CI 포함) — 이유·대안·함정: `docs/decisions/0001-local-docker-postgres.md`. 각 PC에 **Docker Desktop + Node 20 + Python 3.11+** 필요.

## 무엇이 들어가나
**이 레포가 곧 키트다** (2026-10-08 정리). `export.py`는 이 레포의 추적 파일을 그대로 내보내고, 이 레포 전용 파일(`EXCLUDE`: 레포 README·CLAUDE.md·CI·`templates/` 등)만 빼고, 팀 레포용 `overlay/`(팀 `CLAUDE.md`·문서 검사 잡이 있는 CI)와 제출 문서 8개를 넣는다.

| 구분 | 내용 |
|---|---|
| 프론트 | Next.js 16 + TS + Tailwind v4 + shadcn/ui + **KDS 2.0 토큰**, 공용 레이아웃·사이드바(메뉴는 `menu-items.ts`, merge=union)·PageHeader·ErrorLine·AI 라벨·`api-client`(ApiError·detail·204), `/agent`(AI 채팅), `/samples/*`, Vitest |
| 백엔드 | FastAPI(라우터 자동 등록), AI 에이전트 엔진(Claude·Gemini·OpenAI 호환·**mock**), 사용량 한도, `/api/health`(`version`=git SHA), pytest |
| DB | **PostgreSQL** (docker compose `db`, 127.0.0.1:55432), `database/migrations/YYYYMMDDHHMM_*.sql` 서버 시작 시 자동 적용 |
| 파이프라인 | `make setup·dev·sync·verify·serve·e2e·ship·record·claims·submit-check`, `e2e/`, `scripts/e2e-report.py`(TC 결과 자동 기록), `scripts/ai-review.py`(헤드리스 AI 리뷰), `scripts/claim.sh`(Issue 선점), 머지 잠금, `docs/pipeline.md` |
| 작업 규칙 | 팀 `CLAUDE.md`(채점 근거·충돌 방지 규칙), `.claude/` 규칙·스킬(`/plan-topic`→`/new-issue`→`/start-task`→`/handoff`=`make ship`→`/submit`)·reviewer(채점 기준) |
| 제출 문서 | `README.md` + `docs/` 7개, `scripts/check-docs.py`, `docs/submission-guide.md` (`templates/submission/`) |
| PR 점수 | PR Review 워크플로(자동 40점 + AI 리뷰 블록 60점, 비차단) — #80 |
| CI | frontend·backend·docs·e2e, gitleaks (팀 레포에서 Actions가 돌 때) |

## 쓰는 법 (10/14)
```sh
# 0. 배정 레포를 clone (사내 GHE, VPN 연결)
git clone <배정 레포 URL> ~/team-repo

# 1. 미리보기 → 내보내기 (이 레포 루트에서)
python3 templates/starter/export.py ~/team-repo --dry-run
python3 templates/starter/export.py ~/team-repo
```
- 대상에 **이미 있는 파일은 건너뛰고** 목록을 보여 준다 (주최 측이 넣어 둔 README 등). 내용을 비교해 직접 합치거나 `--force`로 덮어쓴다.
- 건너뛴 파일은 키트 버전을 옆에 `<파일>.kit`로 둔다 (예: 주최 측 README → `README.md.kit`). 비교해 합친 뒤 `.kit`을 지운다.
- `.gitignore`가 이미 있으면 덮어쓰지 않고 **빠진 줄만 덧붙인다** (`.env`·`app.db` 커밋 방지). `backend/.gitignore`도 따로 들어간다.
- `docs/security-policy.md`, `.github/ISSUE_TEMPLATE/**`(주최 측 제공)는 `--force`여도 건드리지 않는다.

```sh
# 2. 실행 확인
cd ~/team-repo
make setup && make verify   # 기획 전에는 docs-draft가 "SEC-xx 행 없음"으로 실패할 수 있다 (아래)
make serve                  # 브라우저 http://localhost:3000 확인 후 make stop

# 3. 첫 커밋 (main 보호가 있으면 브랜치 → PR)
git switch -c chore/starter-kit && git add -A && git commit -m "chore: 시작 키트" && git push -u origin chore/starter-kit
```
- 주최 측 `docs/security-policy.md`에 키트 양식(`docs/security-compliance.md`)보다 SEC 항목이 많으면, 기획 전 `make verify`는 `docs-draft`만 "SEC-xx 행 없음"으로 실패한다 (2026-10-09 리허설). 기획(`/plan-topic` 5단계)에서 SEC를 옮기면 풀린다 — 그 전에는 나머지 검사가 PASS인지만 본다.

4. 주제가 나오면 `/plan-topic <주제 원문>` → 기획 게이트 통과 후 `/new-issue`. 이후 단계는 `docs/pipeline.md` (개발 → `make e2e` → `/submit`).
5. 서비스 이름을 바꿀 곳: `frontend/src/app/layout.tsx`(title), `components/app-sidebar.tsx`(배너), `src/app/page.tsx`(홈), `backend/app/agent/prompts.py`(에이전트 역할), `features/chat/ChatView.tsx`(예시 질문).
6. AI 기능이 필요 없는 주제면 `/agent`를 메뉴(`frontend/src/components/menu-items.ts`)에서 빼면 된다 (코드는 남겨도 무방). 주제에 맞는 기능은 `/add-endpoint`·`/add-page`로 추가.

## 사내 GHE에서 CI가 안 돌면
첫 push 뒤 Actions 탭을 확인한다. `actions/checkout` 등을 쓸 수 없어 CI가 시작하지 않으면, PR 전에 `CLAUDE.md` "명령"의 검증을 로컬에서 실행하고 결과를 PR 본문에 붙인다 (`/handoff`가 실행한다).

## 검증 기록
- **CI `starter-kit` 잡**이 PR마다 이 레포에서 키트를 내보내 `make setup → verify → e2e`를 돌린다 (가장 최근 상태는 그 잡 결과).
- 2026-10-08 기준 키트: pytest 56 · Vitest 21 · E2E 3 통과, `make verify` 10개 검사 PASS (gitleaks는 미설치 시 SKIP).
- 2026-10-08 docker compose·PostgreSQL 전환 후(#92·#96·#97): pytest 58(실제 PostgreSQL, 테스트마다 새 schema) · `make verify` 9개 · `make e2e` 전체 PASS, `make serve`(docker db+api+web) 스모크 PASS, `make dev` 핫 리로드(backend·frontend 4초)·실제 Ctrl+C로 컨테이너 정리, DB 꺼진 상태에서 verify·e2e가 db 자동 기동. CI(레포·키트)는 postgres 서비스로 통과.
- 로컬 시뮬레이션 (bare origin + clone 3개): 머지 잠금 직렬화·오래된 잠금 회수, merge 기반 sync, 타임스탬프 마이그레이션 순서, `submit-check`가 막는 경우(커밋 안 된 변경·push 안 함·근거 이후 코드 변경·포맷 오류·dirty 근거·전체 FAIL 근거)
- 실제 GitHub (비공개 테스트 레포, 시험 후 삭제): A·B 동시 `make ship` → 잠금 순서 머지·재반영, AI 리뷰가 실제 버그로 머지를 막음, PR 점수 91/100, Issue 자동 completed + 근거 댓글
- 내보내기: 이미 있는 파일 건너뜀(`.kit`)·`--force`·주최 측 파일 보호·`.gitignore` 병합·재실행 시 변경 0개

## 리허설 (2026-10-08, 비공개 레포 + 가짜 주제 "회의실 예약", A·B 두 명)
| 단계 | 걸린 시간 | 결과 |
|---|---|---|
| 키트 설치 (`export` → `make setup·verify`) | 약 30초 | 주최 측 README는 `README.md.kit`로 남겨 합침 |
| 기획 `/plan-topic` | 5분 19초 | REQ 6 · AC 21 · TC 26 · SEC 4, 가정 11개, 3명 분할안 — 문서 검사 오류 0 |
| 공용 기반 PR (계약·마이그레이션·client-id) | 약 3분 + ship 3분 | 자동 머지 |
| REQ 하나 (Claude 구현 → `make ship`) | 구현 3~6분, ship 3~4분 | 4개 모두 자동 머지, Issue 4개 CLOSED COMPLETED, AI 리뷰 52~54/60 |
| `make record` | 2분 24초 | TC 18개 전부 PASS, REQ-01~04 `검증됨` |
| `make submit-check` | — | 남은 것: 문서 자리표시(README·experience·development), 제외한 REQ의 TC — **문서 마무리 시간(20:00~22:00)이 필요** |

리허설에서 막힌 것과 키트에 반영한 것:
- **순환 의존**: 등록 REQ의 E2E가 아직 없는 목록 API로 저장을 확인, 목록 REQ의 E2E는 등록 API를 써서 둘 다 머지 불가 → `/plan-topic`에 머지 순서·"앞선 REQ API만" 규칙, `/start-task`에 의존 확인
- **같은 줄 충돌**: 메뉴 import 줄·arch 표 인접 행 → `menu-items.ts` merge=union, arch REQ별 블록 (기획 때 미리)
- **api-client**가 서버 오류 문구·204를 못 다룸 → ApiError
- **격리 E2E 포트 충돌**(한 PC에서 두 ship) → 빈 포트 자동 선택
- 제외한 REQ의 TC는 `SKIP(REQ-11 제외)`로 적어야 strict 검사를 통과한다

## 관리
- 공용 코드·스크립트·스킬은 **이 레포에서 고치면 그대로 키트가 된다**. 팀 레포용으로 달라야 하는 파일만 `overlay/`에, 이 레포 전용 파일은 `export.py`의 `EXCLUDE`에.
- CI `starter-kit` 잡이 PR마다 키트를 내보내 `make setup·verify·e2e`를 돌린다. `PATCHES`(README 실행 구역)의 원본 문자열이 바뀌면 내보내기가 실패해서 알 수 있다.
