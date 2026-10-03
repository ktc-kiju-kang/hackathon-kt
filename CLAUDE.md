# KT 해커톤 프로젝트

> 3명이 동시에 Claude Code로 작업하는 레포. **이 파일은 팀 공용 규칙**이며, 개인 메모는 `CLAUDE.local.md`(gitignore됨)에 쓴다.
> 저장소는 **공개**다. 키·토큰·개인정보는 절대 커밋하지 않는다.

## 개요
- 주제: **KT Group AI Opportunity Radar** — OpenAI Signals(공개 ChatGPT 사용 데이터)로 AI 활용 트렌드를 분석해 KT 그룹사 사업과 매칭하고, 사업기회 → 프로덕트·PoC 설계까지 만들어 주는 에이전트 (기획·데이터·MVP 범위: `docs/PROJECT.md`, 시연 체크리스트: `docs/DEMO.md`)
- 저장소: https://github.com/ktc-kiju-kang/hackathon-kt
- 칸반: https://github.com/users/ktc-kiju-kang/projects/1 (GitHub Projects "KT 해커톤") — 카드 = 이슈
- 프론트(배포): https://hackathon-kt.vercel.app (Vercel, PR마다 프리뷰 URL)
- API(배포): https://hackathon-kt-api.onrender.com/api/docs
- DB: Supabase 팀 공유 프로젝트 1개 — `https://atirjbxwroqkbopnqybz.supabase.co` (ap-southeast-1, Render와 같은 리전)
- 상태 확인: `/api/health` → `version`(배포 커밋), `db`(Supabase 연결·service_role 키: ok/error/unconfigured), `llm`(anthropic/gemini/openai/mock), `client_ip`(사용량 한도에 쓰는 내 IP)
- 화면: `/` 홈 · `/trends` AI 활용 트렌드 · `/radar` Opportunity Radar · `/product` Product Generator · `/agent` AI 에이전트 · `/samples/*` UI 샘플 (메뉴: `components/app-sidebar.tsx`)
- 데모 흐름: `/trends`(Signals 지표) → `/radar`(그룹사 선택 → 근거 있는 사업 기회) → `/product`(Product Card·PoC, Markdown 내보내기). 계약: `docs/contracts/{trends,radar,product}.md`

## 작업 방식: 기능 단위 담당
- 역할·디렉터리 고정 담당은 없다. **이슈(기능) 하나를 한 사람이 frontend + backend + DB까지 끝까지** 맡는다.
- 담당자 = 이슈 assignee. 칸반 Todo에서 카드를 가져가며 본인을 assign한다.
- 카드 이동: 이슈 생성 → Todo(자동), 작업 시작 → In Progress(`/start-task`), PR 연결 → In Review(자동), 머지 → Done(자동). 상세는 `docs/TEAM.md`
- 파일을 **기능별로 나눠** 서로 다른 기능이 같은 파일을 건드리지 않게 한다 (구조·분업 규칙: `docs/architecture.md`).

## 문서 지도 (필요할 때 읽는다)
| 하려는 일 | 읽을 곳 | 로딩 |
|---|---|---|
| frontend 코드 작성·수정 | `.claude/rules/frontend.md` | `frontend/**`를 다룰 때 자동 |
| backend 코드·테스트·DB | `.claude/rules/backend.md` | `backend/**`를 다룰 때 자동 |
| AI 에이전트·LLM·구조화 생성·eval | `.claude/rules/agent.md` | agent·evals·chat/radar/product 서비스를 다룰 때 자동 |
| 어디에 만들지·분업·import 방향 | `docs/architecture.md` (결정: ADR 0007) | 링크 |
| 배포·환경변수 | `docs/deploy.md` | 링크 |
| SDLC 단계·완료 정의·테스트 전략·되돌리기·장애 대응 | `docs/SDLC.md` | 링크 |
| 기획·MVP / 시연 / 계약 / 결정 / 작업 기록 / 팀·칸반 | `docs/PROJECT.md` / `docs/DEMO.md` / `docs/contracts/` / `docs/decisions/` / `docs/worklog/` / `docs/TEAM.md` | 링크 |

> 규칙 파일은 해당 경로의 파일을 읽거나 고칠 때 자동으로 들어온다. 작업을 시작하기 전에 규칙이 필요하면 직접 읽는다.

## 구조 (요약 — 상세·목표 구조·import 규칙: `docs/architecture.md`)
- `frontend/` Next.js(App Router)+TS+Tailwind v4+shadcn/ui: `src/app/<route>/`(화면) · `src/features/<feature>/`(기능 폴더, `api.ts`) · `src/components/`·`src/lib/`(공용)
- `backend/` FastAPI: `app/{routers,services,schemas}/<feature>.py`(기능) · `app/core/`(공용: config·db·quota) · `app/agent/`(AI 엔진, 공용) · `data/` · `evals/` · `tests/`
- `database/migrations/`, `docs/{contracts,decisions,worklog}/`
- 핵심: **features끼리 직접 import 금지**, 공용 코드는 기능 폴더에 두지 않고 별도 PR로, backend 새 기능은 현재 구조(`routers`·`services`·`schemas`)로.

## 명령
| | frontend (`cd frontend`) | backend (`cd backend`) |
|---|---|---|
| 셋업 | `npm install && cp .env.example .env.local` | `uv venv && uv pip install -r requirements-dev.txt && cp .env.example .env` |
| 실행 | `npm run dev` → :3000 | `.venv/bin/fastapi dev app/main.py` → :8000 (`/api/docs`) |
| 검증 | `npm run lint && npm test && npm run build` | `.venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/ty check app tests evals && .venv/bin/pytest` |

**PR 전 변경한 쪽의 검증 명령을 반드시 통과시킨다.** CI(`frontend`, `backend` 잡)가 동일하게 실행한다.

## 협업 규칙 (Claude도 반드시 따를 것)
1. **이슈 없이 기능 작업을 시작하지 않는다.** 칸반 카드(이슈)를 먼저 만들고 assign한다. (`/new-issue`)
2. **main 직접 커밋·push 금지.** main 보호: PR + CI 통과. **승인은 필수가 아니다** — CI가 통과하면 작성자가 직접 머지할 수 있다.
   - 브랜치: `<type>/<이슈번호>-<짧은설명>` (예: `feat/12-login-page`, `fix/20-cors`). type: feat/fix/refactor/docs/chore
   - 이슈 없는 인프라·문서 작업만 `<type>/<설명>` 허용
   - PR 본문에 `Closes #<이슈번호>` → 머지 시 이슈 닫힘·카드 Done. 머지된 브랜치는 자동 삭제
   - 리뷰 권장(머지 전에 리뷰어 지정): 공용 파일(규칙 5), 남의 기능 파일(규칙 6), 다른 기능이 쓰는 계약(규칙 4), DB 마이그레이션. 리뷰를 요청했으면 답을 받고 머지한다
3. **동시에 여러 이슈는 worktree로:** `scripts/new-worktree.sh <이슈번호> <설명>`
4. **계약 우선:** 다른 기능·화면이 쓰는 API는 `docs/contracts/<feature>.md`에 먼저 정의한다. 남의 기능 계약을 바꾸면 그 담당자를 PR 리뷰어로 지정한다.
5. **공용 파일은 최소한으로, 작게 고친다:** `layout.tsx`, `src/app/page.tsx`, `app-shell.tsx`, `app-sidebar.tsx`(메뉴 한 줄 추가는 OK), `api-client.ts`, `components/`, `app/core/`, `app/agent/`(loop·providers·prompts·types·structured — `tools/<name>.py` 제외), `requirements*.txt`, `package.json`, 루트 설정. 큰 변경은 별도 PR로 먼저 머지한다.
6. **남의 기능 파일은 직접 고치지 않는다.** 필요하면 담당자에게 요청하거나, 사용자 확인 후 수정하고 담당자를 리뷰어로 지정한다.
7. **DB 마이그레이션은 main 머지 시 공유 DB에 자동 적용된다.** 번호는 머지 직전에 확정. 마이그레이션은 backend 배포보다 먼저 적용되므로 **이전 버전 코드와도 호환**되게 쓴다(컬럼 추가 OK, drop/rename은 2단계로). 파괴적 변경은 팀에 먼저 알린다.
8. **작게, 자주 머지.** 작업 시작 전과 PR 전에 `scripts/sync.sh`로 main 반영. **PR 전에는 `scripts/check-conflicts.sh`(`/pr-check`)로 충돌 검사** — git이 아직 모르는 충돌(같은 화면 경로를 두 사람이 만듦, 마이그레이션 번호 중복, 다른 열린 PR과 같은 파일)까지 찾는다.
9. 커밋: `<type>(<feature>): <요약>` — 예: `feat(login): 로그인 폼 추가`

## SDLC 한눈에 (상세·완료 정의·테스트 전략·되돌리기·장애 대응: `docs/SDLC.md`)
| 단계 | 방식 | 도구 |
|---|---|---|
| 요구사항 | 이슈 하나 = 기능 하나 (목표·완료 조건), 칸반 자동 이동 | `/new-issue` |
| 설계 | 계약 우선(`docs/contracts/`), 큰 결정은 ADR | `/add-endpoint` |
| 구현 | 브랜치 `<type>/<이슈>-…`, 기능 폴더, 작게 자주 머지 | `/start-task` `/add-page` `/add-agent-tool` |
| 테스트 | backend pytest(DB·LLM 없이)·frontend Vitest·evals(실비용)·lint·build, CI 필수 | `.claude/rules/backend.md` |
| 리뷰 | 셀프 리뷰 + 충돌 검사, 공용 파일은 리뷰 요청 | `reviewer` `/pr-check` `/handoff` |
| 배포 | main 머지 → CI → migrate → backend → frontend → smoke | `docs/deploy.md` `/deploy-status` |
| 운영·회고 | `/api/health`, 장애 대응표, 날짜별 작업 기록 | `docs/SDLC.md` `docs/worklog/` |

## Claude 작업 방식
- 세션 시작 시 훅이 브랜치·동기화 상태, 내 이슈, 열린 PR을 보여준다. main보다 뒤처져 있으면 먼저 `/sync`를 제안한다.
- 스킬 흐름: `/new-issue` → `/start-task` → (`/add-endpoint`·`/add-page`·`/add-agent-tool`) → `/pr-check` → `/handoff`. 보조: `/sync`·`/team-status`·`/deploy-status`. 설명은 각 스킬 파일의 frontmatter.
- PR 전에는 `reviewer` 서브에이전트로 셀프 리뷰.
- **다른 사람 PR의 충돌을 풀 때**는 그 브랜치에 main을 merge한다 (rebase·force push로 남의 기록을 바꾸지 않는다). 남의 기능 파일이 걸리면 선택지를 사용자에게 묻는다.
- 이슈 생성·push·PR 생성·수동 재배포는 사용자 확인 후. PR 머지는 사람이 한다. 공유 DB에 직접 SQL을 실행하지 않는다 (마이그레이션 파일 + 배포 파이프라인으로만).
