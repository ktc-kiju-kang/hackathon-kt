# {{서비스 이름}} — 팀 {{팀 번호}}

> 3명이 동시에 Claude Code로 작업하는 레포. **이 파일은 팀 공용 규칙**이며, 개인 메모는 `CLAUDE.local.md`(gitignore됨)에 쓴다.
> 키·토큰·개인정보는 절대 커밋하지 않는다. 데이터는 합성 데이터만 쓴다.

## 개요
- 주제: {{주제 번호·이름}} — 요구사항 원본은 `docs/prd.md` (REQ·AC)
- 개발 마감: **2026-10-15 00:00**. 제출 = 포털에 이 레포의 40자 commit SHA + 발표자료
- 실행: 로컬 (외부 서비스 없음). DB는 SQLite, LLM은 키가 없으면 mock
- 상태 확인: `GET /api/health` → `version`(실행 중인 커밋), `db`(ok/error), `llm`(anthropic/gemini/openai/mock)

## 채점 근거 — 모든 작업이 지키는 규칙
기술평가는 AI가 **문서·코드·실행/테스트 결과·GitHub 이력·AI 활용 기록**을 보고 매긴다. 분량·Issue 수·토큰 사용량은 점수가 아니다.
1. **ID 사슬**: REQ(`docs/prd.md`) → AC(`prd.md`) → Issue·코드(`docs/arch.md` "REQ별 코드 위치") → TC(`docs/e2e-test.md`) → 실제 결과. 새 기능은 REQ·AC부터 적는다.
2. **실행한 것만 결과로 적는다.** TC의 실제 결과·PASS/FAIL은 명령을 실제로 실행한 출력으로만 채운다. 실행하지 않았으면 `미실행`, 확인 못 했으면 `미검증`. 계획·예시를 완료로 쓰지 않는다.
3. **보안**: `docs/security-policy.md`(주최 제공)는 **수정하지 않는다**. SEC별 적용·코드 위치·정상/거부 시험 결과를 `docs/security-compliance.md`에 남긴다.
4. **AI 활용 기록**: AI가 틀린 것을 사람이 잡았거나 고친 사례는 바로 `docs/development.md` "AI 활용 기록"에 한 줄 추가한다 (작업·AI가 한 것·확인 방법·고친 것·커밋).
5. 문서 검사: `python3 scripts/check-docs.py --draft` (작성 중) / `python3 scripts/check-docs.py` (제출 직전, 오류 0). 사용법: `docs/submission-guide.md`
6. AI 사용 기록 수집기(kode:ton)가 켜져 있어야 한다. PC 재시작 후 앱을 다시 실행한다.

## 작업 방식: 기능 단위 담당
- **Issue 하나 = REQ 하나**를 한 사람이 frontend + backend + DB + 시험까지 끝까지 맡는다. 담당자 = Issue assignee.
- Issue는 **주최 측 양식(개발 작업·검증)** 으로 만든다. 제목 `[REQ-01] <요약>`. 완료 조건 = prd.md의 AC.
- 완료: Issue 본문에 **커밋 주소와 테스트 명령·결과**를 붙이고 닫는다. PR 본문 `Closes #<번호>`로 머지하면 completed로 닫힌다. 직접 닫을 때는 **Close as completed**. 취소·중복은 사유를 남기고 Close as not planned. (Projects의 Done 이동·체크박스만으로는 완료로 집계되지 않는다)
- 파일을 기능별로 나눠 서로 다른 기능이 같은 파일을 건드리지 않게 한다.

## 문서 지도
| 하려는 일 | 읽을 곳 | 로딩 |
|---|---|---|
| frontend 코드 | `.claude/rules/frontend.md`, `.claude/rules/kds.md` | `frontend/**`를 다룰 때 자동 |
| backend 코드·테스트·DB | `.claude/rules/backend.md`, `database/README.md` | `backend/**`를 다룰 때 자동 |
| AI 에이전트·LLM | `.claude/rules/agent.md` | 자동 |
| 제출 문서 8개 | `README.md`, `docs/{project-brief,prd,arch,experience,development,security-compliance,e2e-test}.md`, 사용법 `docs/submission-guide.md` | 링크 |
| API 계약 | `docs/contracts/` | 링크 |

## 구조
- `frontend/` Next.js(App Router)+TS+Tailwind v4+shadcn/ui (KDS 2.0 토큰): `src/app/<route>/`(화면) · `src/features/<feature>/`(기능, `api.ts`) · `src/components/`·`src/lib/`(공용)
- `backend/` FastAPI: `app/{routers,services,schemas}/<feature>.py`(기능, 라우터 자동 등록) · `app/core/`(config·db·quota) · `app/agent/`(AI 엔진) · `tests/`
- `database/migrations/` SQLite 마이그레이션 (서버 시작 시 자동 적용)
- 핵심: **features끼리 직접 import 금지**, 공용 코드는 기능 폴더에 두지 않는다.

## 명령
| | frontend (`cd frontend`) | backend (`cd backend`) |
|---|---|---|
| 셋업 | `npm install && cp .env.example .env.local` | `python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt && cp .env.example .env` |
| 실행 | `npm run dev` → :3000 | `.venv/bin/fastapi dev app/main.py` → :8000 (`/api/docs`) |
| 검증 | `npm run lint && npm test && npm run build` | `.venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/ty check app tests && .venv/bin/pytest` |

**PR 전 변경한 쪽의 검증 명령을 반드시 통과시킨다.** CI가 있으면 같은 명령을 실행한다.

## 협업 규칙 (Claude도 반드시 따를 것)
1. **Issue 없이 기능 작업을 시작하지 않는다.** (`/new-issue`)
2. **main 직접 커밋·push 금지.** 브랜치 `<type>/<이슈번호>-<짧은설명>` (type: feat/fix/refactor/docs/chore) → PR → 검증 통과 후 머지. PR 본문 첫 줄 `Closes #<번호>`.
3. 동시에 여러 Issue는 worktree로: `scripts/new-worktree.sh <이슈번호> <설명>`
4. **계약 우선**: 다른 화면이 쓰는 API는 `docs/contracts/<feature>.md`에 먼저 정의한다.
5. 공용 파일(`layout.tsx`, `src/app/page.tsx`, `app-shell.tsx`, `app-sidebar.tsx`(메뉴 한 줄은 OK), `api-client.ts`, `components/`, `app/core/`, `app/agent/`(`tools/<name>.py` 제외), `requirements*.txt`, `package.json`, 루트 설정)은 작게 고치고 팀에 알린다.
6. 남의 기능 파일은 직접 고치지 않는다. 필요하면 담당자에게 요청한다.
7. DB 마이그레이션 번호는 머지 직전에 확정한다. 적용된 파일은 고치지 않고 새 파일을 추가한다.
8. 작게, 자주 머지. 작업 시작 전과 PR 전에 `scripts/sync.sh`, PR 전에 `scripts/check-conflicts.sh`(`/pr-check`).
9. 커밋: `<type>(<feature>): <요약>` — 예: `feat(todo): 할 일 등록 API (REQ-01)`

## Claude 작업 방식
- 스킬 흐름: `/new-issue` → `/start-task` → (`/add-endpoint`·`/add-page`·`/add-agent-tool`) → `/pr-check` → `/handoff`. 보조: `/sync`·`/team-status`.
- PR 전에는 `reviewer` 서브에이전트로 셀프 리뷰.
- Issue 생성·push·PR 생성은 사용자 확인 후. PR 머지는 사람이 한다.
- 사내 GitHub Enterprise면 `gh`가 그 호스트를 보게 한다: `gh auth login --hostname <호스트>` 후 레포 안에서 실행 (또는 `GH_HOST=<호스트>`).
