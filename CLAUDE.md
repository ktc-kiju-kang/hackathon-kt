# KT 해커톤 본선 준비 레포 — 시작 키트 원본

> 3명이 Claude Code로 작업하는 레포. **이 파일은 팀 공용 규칙**이며, 개인 메모는 `CLAUDE.local.md`(gitignore됨)에 쓴다.
> 저장소는 **공개**다. 키·토큰·개인정보는 절대 커밋하지 않는다. 주최 측 자료(`hackathon-rules/`, gitignore)는 올리지 않는다.

## 개요
- 목적: 본선(2026-10-14 주제 공개 → **10-15 00:00 마감**)에서 배정 레포에 깔 **시작 키트의 원본이자 연습장**. 이 레포 자체가 키트와 같은 구조로 돌아간다 (로컬 전용: SQLite, mock LLM, `make`).
- 채점: 기술 70(AI가 문서·코드·실행/테스트 결과·GitHub 이력·AI 활용 기록을 평가, 보안 10 포함) + 동료 10 + 심사위원 20. 상세·제출 절차는 `templates/submission/GUIDE.md`.
- 배정 레포에 깔기: `python3 templates/starter/export.py <배정 레포> --dry-run` → 실제 실행 (`templates/starter/README.md`). 이 레포에서 고친 공용 코드·스크립트·스킬이 그대로 키트가 된다.
- 레포: https://github.com/ktc-kiju-kang/hackathon-kt · 이전 주제(AI Opportunity Radar)·Vercel/Render/Supabase 배포는 2026-10-08에 정리했다 (git 이력에 남음).

## 이 레포에서 고칠 때
- 팀 레포에서도 똑같이 돌아야 한다. PR 전에 `make verify` + 키트를 내보내 확인한다 (CI `starter-kit` 잡이 PR마다 `export.py` → `make setup·verify·e2e`를 돌린다).
- 팀 레포용으로 **달라야 하는** 파일만 `templates/starter/overlay/`(팀 `CLAUDE.md`·CI)에 둔다. 이 레포 전용 파일은 `export.py`의 `EXCLUDE`에 넣는다. 그 밖에는 이 레포 파일이 그대로 키트다.
- 제출 문서 8개는 `templates/submission/`에만 있다 (이 레포 루트에는 없어서 `make verify`의 문서 검사는 SKIP, `make e2e` 근거는 `.run/evidence/`).
- 리허설 기록·교훈: `templates/starter/README.md` "리허설".

## 문서 지도
| 하려는 일 | 읽을 곳 | 로딩 |
|---|---|---|
| frontend 코드 | `.claude/rules/frontend.md`, `.claude/rules/kds.md` | `frontend/**`를 다룰 때 자동 |
| backend 코드·테스트·DB | `.claude/rules/backend.md`, `database/README.md` | `backend/**`를 다룰 때 자동 |
| AI 에이전트·LLM | `.claude/rules/agent.md` | 자동 |
| 파이프라인 (단계·게이트·시간표·장애 대응) | `docs/pipeline.md` | 링크 |
| 키트 내보내기·리허설 | `templates/starter/README.md` | 링크 |
| 제출 문서 8개·채점 근거 | `templates/submission/GUIDE.md` | 링크 |
| PR 자동 점검 점수 (#80) | `docs/superpowers/specs/2026-10-03-pr-review-scoring-design.md`, `scripts/pr_review_score.py` | 링크 |
| API 계약 | `docs/contracts/` | 링크 |

## 충돌 방지 규칙 (세 사람이 같은 것을 동시에 고치지 않게)
| 충돌 원인 | 규칙 | 장치 |
|---|---|---|
| 같은 Issue | 세 사람이 같은 Issue를 동시에 잡지 않는다 — 선점은 GitHub의 `claim/<번호>` 브랜치를 **없을 때만** 만드는 것으로 판정(assignee는 여러 명이 될 수 있어 판정에 안 씀). 손 떼면 `make release ISSUE=<번호>` | `/start-task`(`scripts/claim.sh take`), `make ship`(남이 잡은 Issue면 멈춤, 머지 후 해제), `make claims` |
| 같은 파일 | 기능별 폴더(`features/<f>/`, `{routers,services,schemas}/<f>.py`, `tests/test_<f>.py`, `e2e/test_<f>.py`). 남의 기능 파일은 고치지 않고 담당자에게 요청 | `make ship`의 충돌 검사(열린 PR과 같은 파일·기능이면 경고) |
| 공용 파일 | `layout.tsx`, `src/app/page.tsx`, `app-shell.tsx`, `app-sidebar.tsx`, `api-client.ts`, `components/`, `app/core/`, `app/agent/`(`tools/<name>.py` 제외), `prompts.py`, 루트 설정 — **작은 단독 PR**(`chore/shared-<설명>`)로 먼저 ship | reviewer가 "설계·구조"에서 감점 |
| 메뉴·코드 위치 | 메뉴는 `frontend/src/components/menu-items.ts`에 import 한 줄 + 항목 한 줄만 추가 (기존 줄 수정 금지). `docs/arch.md` "REQ별 코드 위치"는 **자기 REQ 블록만** 고친다 | `.gitattributes` `merge=union`(메뉴), 블록 사이 빈 줄(arch) — 동시에 추가해도 충돌 없음 |
| 머지 순서 | 기획 때 REQ 머지 순서를 정하고, E2E는 자기 REQ와 **앞선 REQ의 API만** 쓴다 (순환 의존이면 둘 다 머지 못 함) | `/plan-topic`, `/start-task` 의존 확인 |
| 의존성 | `package.json`·`package-lock.json`·`requirements*.txt` 변경은 **단독 PR**(`chore/deps-<이름>`). 모두 Node 20/npm 10(`.nvmrc`) | `make setup`이 버전 경고, `make sync`가 "make setup 필요" 안내 |
| DB 마이그레이션 | 파일 이름 = 만든 시각 `YYYYMMDDHHMM_<설명>.sql` → 번호 경쟁 없음. 적용된 파일은 고치지 않는다 | `core/db.py`가 이름 형식 검사 |
| 시험 기록 문서 | `docs/e2e-test.md` 상태·`docs/prd.md` 상태·`docs/evidence/`는 **기능 PR에 넣지 않는다**. 기록 담당 1명이 main에서 `make record` | `make ship`이 시험 후 기록을 되돌림, record PR은 기록 파일만 허용 |
| 동시 머지 | 한 번에 한 명만 머지 — GitHub의 `merge-lock` 브랜치로 잠금, 그사이 main이 바뀌면 다시 반영·검사 후 머지 | `make ship` 8단계, `make lock-status` |
| 오래 열린 브랜치 | 반나절 넘기지 않는다. 시작 전·중간에 `make sync`(merge, force push 불필요) | `make ship` 1단계가 항상 main을 먼저 반영 |
| 같은 화면 경로 | 시작 전 `ls frontend/src/app` + 열린 PR 확인. 경로 = 기능 이름 | 충돌 검사(같은 경로 ❌) |

## 구조
- `frontend/` Next.js(App Router)+TS+Tailwind v4+shadcn/ui (KDS 2.0 토큰): `src/app/<route>/`(화면) · `src/features/<feature>/`(기능, `api.ts`) · `src/components/`·`src/lib/`(공용)
- `backend/` FastAPI: `app/{routers,services,schemas}/<feature>.py`(기능, 라우터 자동 등록) · `app/core/`(config·db·quota) · `app/agent/`(AI 엔진) · `tests/`
- `database/migrations/` SQLite 마이그레이션 (서버 시작 시 자동 적용)
- `e2e/` 배포된 서버에 HTTP로 붙는 E2E 시험 (`make e2e`) · `scripts/` 파이프라인 스크립트 · `docs/evidence/` 시험 근거 (팀 레포에서 자동 생성·커밋. 이 레포는 `.run/evidence/`)
- 핵심: **features끼리 직접 import 금지**, 공용 코드는 기능 폴더에 두지 않는다.

## 명령 (입구는 `make`, 상세 `docs/pipeline.md`)
| 명령 | 언제 |
|---|---|
| `make setup` | 처음 한 번, 의존성이 바뀌면 다시 |
| `make dev` | 개발 (핫 리로드, api :8000 + web :3000, 이 PC에서만) |
| `make sync` | 작업 시작 전·중간 — 최신 main을 내 브랜치에 merge |
| `make verify` | 수시로 — CI와 같은 검사 전부 (ship도 실행) |
| **`make ship`** | **작업 끝 — 검사·시험·PR·AI 리뷰·자동 머지** |
| `make serve` / `make stop` / `make status` | 로컬 배포 (프로덕션 빌드 + 스모크) |
| `make e2e` | 시험 전부 + 격리 배포 E2E (확인용. 기록 커밋은 `make record`) |
| `make record` | 기록 담당: main에서 시험 기록을 자동 PR로 머지 (2~3시간마다, 제출 전) — **팀 레포 전용** |
| `make lock-status` | 누가 머지 중인지 |
| `make claims` / `make release ISSUE=12` | 누가 어떤 Issue를 잡았는지 / 내 선점 해제 |
| `make submit-check` | 제출 직전 → 포털에 넣을 SHA — **팀 레포 전용** (`make docs`도 제출 문서가 있어야 의미 있음) |

개별 명령: frontend `npm run lint && npm test && npm run build`, backend `.venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/ty check app tests && .venv/bin/pytest`, E2E `backend/.venv/bin/python -m pytest e2e` (서버가 떠 있을 때).

## 협업 규칙 (Claude도 반드시 따를 것)
1. **Issue 없이 기능 작업을 시작하지 않는다.** (`/new-issue`) 문서·공용·의존성 작업은 `docs/`·`chore/` 브랜치로 Issue 없이 가능.
2. **main 직접 커밋·push 금지.** 브랜치 `<type>/<이슈번호>-<짧은설명>` (type: feat/fix/refactor/docs/chore/test/perf/ci) → `make ship`. 머지는 ship만 한다 (squash).
3. 동시에 여러 Issue는 worktree로: `scripts/new-worktree.sh <이슈번호> <설명>` — 각 worktree에서 `make setup` 후 따로 ship.
4. **계약 우선**: 다른 화면이 쓰는 API는 `docs/contracts/<feature>.md`에 먼저 정의해 작은 PR로 ship한다.
5. 위 "충돌 방지 규칙"을 지킨다. 걸리면 멈추고 사용자에게 묻는다.
6. 커밋: `<type>(<feature>): <요약>` — 예: `feat(todo): 할 일 등록 API (REQ-01)` (PR 점수의 커밋 규약 항목).
7. AI 리뷰가 "수정 필요"면 지적을 고친다. 리뷰를 다시 돌려 점수를 올리려고 코드를 바꾸지 않고 내용을 고친다. 테스트를 지우거나 skip으로 통과시키지 않는다.

## Claude 작업 방식
- 스킬 흐름: `/new-issue` → `/start-task` → (`/add-endpoint`·`/add-page`·`/add-agent-tool`) → `/handoff`(= `make ship`). 보조: `/sync`·`/pr-check`·`/team-status`. 본선용: `/plan-topic`·`/submit`.
- Issue 생성은 사용자 확인 후. **`make ship`(push·PR·자동 머지 포함)은 사용자가 "ship"·"진행"으로 요청했을 때 실행한다.** ship이 멈추면 원인을 설명하고 고칠 방법을 제안한다.
- **자동 큐 `/ticket-loop`**(`/loop 5m /ticket-loop`): 루프를 시작한 것을 "ship" 요청으로 본다. 열린 Issue를 `scripts/claim.sh`로 선점하고 명세·댓글대로 구현해 `make ship`까지 한다. **기본은 `SHIP_NO_MERGE=1`(PR·AI 리뷰까지, 머지는 사람)** 이고, 머지까지 맡기려면 사용자가 `TICKET_LOOP_MERGE=1`로 시작한다. main 직접 push·force push·남의 브랜치·Issue 생성은 제외.
- 같은 작업 폴더에서 다른 Claude 세션이 일하고 있을 수 있다. 큰 작업은 `scripts/new-worktree.sh`로 분리한다.
