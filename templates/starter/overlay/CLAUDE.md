# {{서비스 이름}} — 팀 {{팀 번호}}

> 3명이 동시에 Claude Code로 작업하는 레포. **이 파일은 팀 공용 규칙**이며, 개인 메모는 `CLAUDE.local.md`(gitignore됨)에 쓴다.
> 키·토큰·개인정보는 절대 커밋하지 않는다. 데이터는 합성 데이터만 쓴다.

## 개요
- 주제: {{주제 번호·이름}} — 요구사항 원본은 `docs/prd.md` (인덱스: 원문 SRC·REQ 표) → `docs/prd/REQ-xx-….md` (REQ별 AC)
- 개발 마감: **2026-10-15 00:00**. 제출 = 포털에 이 레포의 40자 commit SHA + 발표자료
- 실행: 로컬 (외부 서비스 없음). 각자 PC의 docker compose — DB는 PostgreSQL(`db` 서비스), LLM은 키가 없으면 mock
- 상태 확인: `GET /api/health` → `version`(실행 중인 커밋), `db`(ok/error), `llm`(anthropic/gemini/openai/mock)

## 채점 근거 — 모든 작업이 지키는 규칙
기술평가는 AI가 **문서·코드·실행/테스트 결과·GitHub 이력·AI 활용 기록**을 보고 매긴다. 분량·Issue 수·토큰 사용량은 점수가 아니다.
1. **ID 사슬**: SRC·REQ(`docs/prd.md`) → AC(`docs/prd/REQ-xx-….md`) → Issue·코드(`docs/arch.md` "REQ별 코드 위치") → TC(`docs/e2e-test.md`) → 실제 결과. 새 기능은 REQ·AC부터 적는다.
2. **실행한 것만 결과로 적는다.** TC의 실제 결과·PASS/FAIL은 명령을 실제로 실행한 출력으로만 채운다. 실행하지 않았으면 `미실행`, 확인 못 했으면 `미검증`. 계획·예시를 완료로 쓰지 않는다.
3. **보안**: `docs/security-policy.md`(주최 제공)는 **수정하지 않는다**. SEC별 적용·코드 위치·정상/거부 시험 결과를 `docs/security-compliance.md`에 남긴다.
4. **AI 활용 기록**: AI가 틀린 것을 사람이 잡았거나 고친 사례는 바로 `docs/development.md` "AI 활용 기록"에 한 줄 추가한다 (작업·AI가 한 것·확인 방법·고친 것·커밋).
5. 문서 검사: `make docs` (작성 중) / `make submit-check` (제출 직전, strict). 사용법: `docs/submission-guide.md`
6. **시험 결과는 `make e2e`가 기록한다**: 테스트 이름에 TC ID(`test_tc_01_3_...`)를 넣으면 `docs/e2e-test.md` 상태·근거와 `docs/prd.md` REQ 상태가 실행 결과로 채워지고 `docs/evidence/`에 원본이 남는다. 손으로 PASS를 적지 않는다 (수동 시험만 예외, 명령·결과를 함께).
7. AI 사용 기록 수집기(kode:ton)가 켜져 있어야 한다. PC 재시작 후 앱을 다시 실행한다.

## 작업 방식: 세 명 · 로컬 PC · 레포 하나 · 자동 리뷰·머지
- 서버 없음. 각자 PC에서 docker compose로 실행한다 (`make dev`/`make serve`, `compose.yaml`). DB는 각자 PC의 PostgreSQL(docker volume), 공유하지 않는다. 검사·시험(`make verify`·`e2e`·`ship`)은 로컬 도구로 돌고 DB만 docker로 자동으로 띄운다 — 그래서 `make setup`과 Docker Desktop 둘 다 필요하다.
- 기본은 **Issue 하나 = REQ 하나**를 한 사람이 frontend + backend + DB + 시험까지 끝까지 맡는다. 담당자 = Issue assignee. 제목 `[REQ-01] <요약>`, 완료 조건 = 하위 정의서의 AC, 양식은 주최 측 "개발 작업·검증". 에이전트에게 역할을 나눠 맡기면 `po`→`pm`→`architect` 에이전트와 `[REQ-01][plan|BE|FE]` 티켓 (`docs/requirements-flow.md`).
- 사람이 하는 일은 **코드 작성 → 커밋 → `make ship`** 이 전부다. ship이 검사·시험·PR·AI 리뷰·Issue 근거 댓글·머지까지 한다. 기준을 넘지 못하면 멈추고 이유를 보여 준다 (`/handoff`).
- 완료: `Closes #<번호>`로 squash 머지되면 Issue가 completed로 닫힌다. 취소·중복은 사유를 남기고 Close as not planned. (Projects Done·체크박스만으로는 완료 집계 안 됨)

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

## 문서 지도
| 하려는 일 | 읽을 곳 | 로딩 |
|---|---|---|
| frontend 코드 | `.claude/rules/frontend.md`, `.claude/rules/kds.md` | `frontend/**`를 다룰 때 자동 |
| backend 코드·테스트·DB | `.claude/rules/backend.md`, `database/README.md` | `backend/**`를 다룰 때 자동 |
| AI 에이전트·LLM | `.claude/rules/agent.md` | 자동 |
| **파이프라인 (단계·게이트·시간표·장애 대응)** | `docs/pipeline.md` | 링크 |
| 요구사항 → 정의서 → 티켓 (PO·PM·역할 에이전트, 티켓의 요구사항 근거) | `docs/requirements-flow.md` | 링크 |
| 제출 문서 8개 | `README.md`, `docs/{project-brief,prd,arch,experience,development,security-compliance,e2e-test}.md`, 사용법 `docs/submission-guide.md` | 링크 |
| API 계약 | `docs/contracts/` | 링크 |
| 결정 기록 (왜 docker compose·PostgreSQL인가 등) | `docs/decisions/` (ADR) | 링크 |

## 구조
- `frontend/` Next.js(App Router)+TS+Tailwind v4+shadcn/ui (KDS 2.0 토큰): `src/app/<route>/`(화면) · `src/features/<feature>/`(기능, `api.ts`) · `src/components/`·`src/lib/`(공용)
- `backend/` FastAPI: `app/{routers,services,schemas}/<feature>.py`(기능, 라우터 자동 등록) · `app/core/`(config·db·quota) · `app/agent/`(AI 엔진) · `tests/`
- `database/migrations/` PostgreSQL 마이그레이션 (서버 시작 시 자동 적용, 규칙 `database/README.md`)
- `e2e/` 배포된 서버에 HTTP로 붙는 E2E 시험 (`make e2e`) · `scripts/` 파이프라인 스크립트 · `docs/evidence/` 시험 근거 (자동 생성, 커밋한다)
- 핵심: **features끼리 직접 import 금지**, 공용 코드는 기능 폴더에 두지 않는다.

## 명령 (입구는 `make`, 상세 `docs/pipeline.md`)
| 명령 | 언제 |
|---|---|
| `make setup` | 처음 한 번, 의존성이 바뀌면 다시 |
| `make dev` | 개발 (docker compose, 핫 리로드, api :8000 + web :3000, 이 PC에서만). docker 없이 `NATIVE=1 make dev` |
| `make sync` | 작업 시작 전·중간 — 최신 main을 내 브랜치에 merge |
| `make verify` | 수시로 — CI와 같은 검사 전부 (ship도 실행) |
| **`make ship`** | **작업 끝 — 검사·시험·PR·AI 리뷰·자동 머지** |
| `make serve` / `make stop` / `make status` | 로컬 배포 (docker compose, 프로덕션 빌드 + 스모크). `make verify`·`e2e`·`ship`은 로컬 도구로 돌고 DB(PostgreSQL)만 docker로 자동 기동 |
| `make db` / `make db-reset` | PostgreSQL만 띄우기(pytest 직접 실행·`NATIVE=1`용) / DB 데이터 전부 삭제 |
| `make e2e` | 시험 전부 + 격리 배포 E2E (확인용. 기록 커밋은 `make record`) |
| `make record` | 기록 담당: main에서 시험 기록을 자동 PR로 머지 (2~3시간마다, 제출 전) |
| `make lock-status` | 누가 머지 중인지 |
| `make claims` / `make release ISSUE=12` | 누가 어떤 Issue를 잡았는지 / 내 선점 해제 |
| `make submit-check` | 제출 직전 → 포털에 넣을 SHA |

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
- 스킬 흐름: `/plan-topic`(기획) → `/new-issue` → `/start-task` → (`/add-endpoint`·`/add-page`·`/add-agent-tool`) → `/handoff`(= `make ship`) → … → `/submit`(제출). 보조: `/sync`·`/pr-check`·`/team-status`. 이슈 현황: `/issue-monitor`(Slack 알림 + 로컬 대시보드).
- Issue 생성은 사용자 확인 후. **`make ship`(push·PR·머지 포함)은 사용자가 "ship"·"진행"으로 요청했을 때 실행한다.** ship이 멈추면 원인을 설명하고 고칠 방법을 제안한다.
- **자동 큐 `/ticket-loop`**(`/loop 5m /ticket-loop`): 루프를 시작한 것을 "ship" 요청으로 본다. 열린 Issue를 `scripts/claim.sh`로 선점하고 명세·댓글대로 구현해 `make ship`까지 한다. **기본은 `SHIP_NO_MERGE=1`(PR·AI 리뷰까지, 머지는 사람)** 이고, 머지까지 맡기려면 사용자가 `TICKET_LOOP_MERGE=1`로 시작한다. main 직접 push·force push·남의 브랜치·Issue 생성은 제외. GitHub 계정당 루프 하나.
- 사내 GitHub Enterprise면 `gh`가 그 호스트를 보게 한다: `gh auth login --hostname <호스트>` 후 레포 안에서 실행 (또는 `GH_HOST=<호스트>`).
