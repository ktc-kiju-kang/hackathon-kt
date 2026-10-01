# KT 해커톤 프로젝트

> 3명이 동시에 Claude Code로 작업하는 레포. **이 파일은 팀 공용 규칙**이며, 개인 메모는 `CLAUDE.local.md`(gitignore됨)에 쓴다.
> 저장소는 **공개**다. 키·토큰·개인정보는 절대 커밋하지 않는다.

## 개요
- 주제: _TBD_
- 저장소: https://github.com/ktc-kiju-kang/hackathon-kt
- 칸반: https://github.com/users/ktc-kiju-kang/projects/1 (GitHub Projects "KT 해커톤") — 카드 = 이슈
- 프론트(배포): https://hackathon-kt.vercel.app (Vercel, PR마다 프리뷰 URL)
- API(배포): https://hackathon-kt-api.onrender.com/api/docs
- DB: Supabase 팀 공유 프로젝트 1개 — `https://atirjbxwroqkbopnqybz.supabase.co` (ap-southeast-1, Render와 같은 리전)
- 상태 확인: `/api/health` → `version`(배포 커밋), `db`(Supabase 연결·service_role 키: ok/error/unconfigured), `llm`(anthropic/gemini/openai/mock)
- 화면: `/` 홈 · `/agent` AI 에이전트 · `/chat` 채팅(임시 UI) · `/samples/*` UI 샘플 (메뉴: `components/app-sidebar.tsx`)

## 작업 방식: 기능 단위 담당
- 역할·디렉터리 고정 담당은 없다. **이슈(기능) 하나를 한 사람이 frontend + backend + DB까지 끝까지** 맡는다.
- 담당자 = 이슈 assignee. 칸반 Todo에서 카드를 가져가며 본인을 assign한다.
- 카드 이동: 이슈 생성 → Todo(자동), 작업 시작 → In Progress(`/start-task`), PR 연결 → In Review(자동), 머지 → Done(자동). 상세는 `docs/TEAM.md`
- 파일을 **기능별로 나눠** 서로 다른 기능이 같은 파일을 건드리지 않게 한다 (아래 "구조"의 `<feature>` 파일들).

## 구조
```
frontend/                        Next.js(App Router) + TS + Tailwind v4 + shadcn/ui
  src/app/<route>/page.tsx         화면(라우트) — 기능 담당자
  src/features/<feature>/          기능별 컴포넌트·api.ts(타입+호출+mock) — 기능 담당자
  src/components/ui/               shadcn 생성 컴포넌트 (공용)
  src/components/app-shell.tsx     좌측 사이드바 + 상단 헤더(h-12) 레이아웃 (공용)
  src/components/app-sidebar.tsx   메뉴 — MENU_GROUPS 배열에 항목 추가 (공용, 한 줄씩)
  src/components/                  그 밖의 공용 컴포넌트, providers.tsx
  src/lib/api-client.ts            공용 HTTP 클라이언트(request, isMock)
  src/app/layout.tsx, page.tsx     공용 (최소 수정)
backend/                         FastAPI
  app/routers/<feature>.py         엔드포인트 (자동 등록) — 기능 담당자
  app/services/<feature>.py        비즈니스 로직·DB 접근 — 기능 담당자
  app/schemas/<feature>.py         Pydantic 요청/응답 모델 — 기능 담당자
  app/main.py, config.py, db.py    공용 (main.py는 수정 불필요)
  app/agent/                       AI 에이전트 엔진 (공용) — providers/ 어댑터, tools/<name>.py 도구(기능 담당자), loop.py
  evals/                           에이전트 평가 (cases.json + run_eval.py)
  tests/test_<feature>.py
database/                        Supabase Postgres
  migrations/NNNN_<설명>.sql       스키마 변경 (규칙: database/README.md)
  seed.sql
docs/contracts/<feature>.md      기능별 API 계약
docs/decisions/                  ADR
```

## 명령
| | frontend (`cd frontend`) | backend (`cd backend`) |
|---|---|---|
| 셋업 | `npm install && cp .env.example .env.local` | `python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt && cp .env.example .env` |
| 실행 | `npm run dev` → :3000 | `.venv/bin/fastapi dev app/main.py` → :8000 (`/api/docs`) |
| 검증 | `npm run lint && npm run build` | `.venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/pytest` |

**PR 전 변경한 쪽의 검증 명령을 반드시 통과시킨다.** CI(`frontend`, `backend` 잡)가 동일하게 실행한다.

## 협업 규칙 (Claude도 반드시 따를 것)
1. **이슈 없이 기능 작업을 시작하지 않는다.** 칸반 카드(이슈)를 먼저 만들고 assign한다. (`/new-issue`)
2. **main 직접 커밋·push 금지.** main 보호: PR + CI 통과 + 1명 승인.
   - 브랜치: `<type>/<이슈번호>-<짧은설명>` (예: `feat/12-login-page`, `fix/20-cors`). type: feat/fix/refactor/docs/chore
   - 이슈 없는 인프라·문서 작업만 `<type>/<설명>` 허용
   - PR 본문에 `Closes #<이슈번호>` → 머지 시 이슈 닫힘·카드 Done. 머지된 브랜치는 자동 삭제
   - **승인 후 새 커밋을 push하면 승인이 취소된다** → 리뷰 반영 후 리뷰어에게 재승인 요청
3. **동시에 여러 이슈는 worktree로:** `scripts/new-worktree.sh <이슈번호> <설명>`
4. **계약 우선:** 다른 기능·화면이 쓰는 API는 `docs/contracts/<feature>.md`에 먼저 정의한다. 남의 기능 계약을 바꾸면 그 담당자를 PR 리뷰어로 지정한다.
5. **공용 파일은 최소한으로, 작게 고친다:** `layout.tsx`, `src/app/page.tsx`, `app-shell.tsx`, `app-sidebar.tsx`(메뉴 한 줄 추가는 OK), `api-client.ts`, `components/`, `config.py`, `db.py`, `app/agent/`(loop·providers·prompts·types — `tools/<name>.py` 제외), `requirements*.txt`, `package.json`, 루트 설정. 큰 변경은 별도 PR로 먼저 머지한다.
6. **남의 기능 파일은 직접 고치지 않는다.** 필요하면 담당자에게 요청하거나, 사용자 확인 후 수정하고 담당자를 리뷰어로 지정한다.
7. **DB 마이그레이션은 main 머지 시 공유 DB에 자동 적용된다.** 번호는 머지 직전에 확정. 마이그레이션은 backend 배포보다 먼저 적용되므로 **이전 버전 코드와도 호환**되게 쓴다(컬럼 추가 OK, drop/rename은 2단계로). 파괴적 변경은 팀에 먼저 알린다.
8. **작게, 자주 머지.** 작업 시작 전과 PR 전에 `scripts/sync.sh`로 main 반영. **PR 전에는 `scripts/check-conflicts.sh`(`/pr-check`)로 충돌 검사** — git이 아직 모르는 충돌(같은 화면 경로를 두 사람이 만듦, 마이그레이션 번호 중복, 다른 열린 PR과 같은 파일)까지 찾는다.
9. 커밋: `<type>(<feature>): <요약>` — 예: `feat(login): 로그인 폼 추가`

## 코드 규칙

### frontend
- 이 버전의 Next.js는 학습 데이터와 다를 수 있다. API·규칙이 애매하면 `frontend/node_modules/next/dist/docs/`를 먼저 확인한다 (`frontend/AGENTS.md`).
- 기본은 Server Component. 상태·이벤트·브라우저 API가 필요한 컴포넌트만 `'use client'`.
- 데이터·비즈니스 로직은 FastAPI에 둔다. Next.js Route Handler/Server Action에 백엔드 로직을 넣지 않는다.
- UI는 shadcn 컴포넌트 우선: `npx shadcn@latest add <이름>` → `src/components/ui/` (생성 코드 직접 수정 최소화).
- import는 `@/` 별칭, 클래스 병합은 `cn()` (`@/lib/utils`), 아이콘 `lucide-react`, 알림 `sonner`의 `toast`.
- 색상은 테마 토큰(`bg-background`, `text-muted-foreground` 등)만. 다크모드는 `next-themes`(시스템 연동).
- **API 호출은 `src/features/<feature>/api.ts`에서만**, `@/lib/api-client`의 `request` 사용. `isMock`일 때 계약 형태의 mock을 반환해 백엔드 없이도 동작하게 한다.
- effect 본문에서 setState를 동기 호출하지 않는다 (lint 에러). 비동기 콜백(`.then`)에서 호출한다. effect 콜백은 값을 반환하지 않게 `{ }`로 감싼다.
- **새 화면 = 라우트 + 기능 폴더 + 메뉴 한 줄** (`/add-page`). 모든 화면은 `AppShell`(사이드바 + 상단 헤더 `h-12`) 안에 그려진다.
  - 화면 전체 높이를 쓰는 페이지(채팅 등)는 루트를 `h-[calc(100svh-3rem)]`로, 스크롤은 페이지가 아니라 내부 목록(`min-h-0 flex-1 overflow-y-auto`)에서.
  - 같은 이름의 라우트·기능 폴더를 두 사람이 만들지 않게, 시작 전에 `ls frontend/src/app frontend/src/features`와 열린 PR을 확인한다 (`/pr-check`가 PR 전에 다시 잡는다).

### backend
- 기능 = `routers/<feature>.py` + `services/<feature>.py` + `schemas/<feature>.py`.
  - `router = APIRouter(prefix="/<feature>", tags=["<feature>"])`를 정의하면 자동 등록 → `/api/<feature>/...`
  - router는 얇게(검증·응답), 로직·DB 접근은 service에. `response_model` 항상 지정.
- DB는 `app.db.get_supabase()`로 service에서만 접근. 설정·비밀값은 `app/config.py`의 `Settings`로만 읽는다.
- DB 사용 예 (service):
  ```python
  from app.db import get_supabase
  rows = get_supabase().table("items").select("*").eq("owner", uid).execute().data
  ```
  `service_role` 키라 RLS를 우회한다 → **권한 체크(누가 어떤 행에 접근 가능한지)는 service 코드에서** 한다.
- 기능마다 `tests/test_<feature>.py`에 최소 1개 테스트. DB가 필요한 테스트는 service 함수를 monkeypatch해 DB 없이 돌게 한다 (CI에는 DB 없음).
  - 로컬 `backend/.env`에 실제 Supabase 키가 있으면 테스트가 실제 DB에 붙는다. 테스트는 `monkeypatch.setattr(settings, ...)`로 설정을 고정해 **로컬 .env와 무관하게** 통과해야 한다.
- `schema_migrations` 테이블은 배포 파이프라인 전용. 기능에서 읽거나 쓰지 않는다.

### AI 에이전트 (`backend/app/agent/`)
- 흐름: `/api/chat/.../messages` → `loop.run_agent` → LLM 어댑터 → 도구 실행 → 반복 → SSE (`docs/contracts/chat.md`)
- LLM은 **키로 자동 선택**: `ANTHROPIC_API_KEY` → Claude `claude-opus-5-5` / `GEMINI_API_KEY` → Gemini `gemini-3.8-flash`(무료 등급) / 둘 다 없으면 **mock**(규칙 기반 가짜 LLM, 키 없이 UI·루프 개발용). 강제 지정은 `LLM_PROVIDER`, 모델은 `LLM_MODEL`, 생각 깊이는 `LLM_EFFORT`(medium). 운영 상태는 `/api/health`의 `llm`.
  - OpenAI 호환 API(Groq·GitHub Models·OpenRouter·Ollama 등): `LLM_PROVIDER=openai` + `LLM_BASE_URL` + `LLM_MODEL` + `LLM_API_KEY` — 코드 수정 없음 (`providers/openai_compat.py`)
  - 무료 등급(Gemini 등)은 입력이 학습에 쓰일 수 있다 → 개인정보·사내 데이터를 넣지 않는다. 분당 요청 제한이 작아 에이전트 왕복이 많으면 429가 날 수 있다.
- **도구 추가 = `app/agent/tools/<name>.py` 파일 하나** (`/add-agent-tool`). 입력은 pydantic, 실행 전 자동 검증. 도구 입력은 신뢰할 수 없는 값으로 다룬다.
- OpenAI 호환이 아닌 LLM 추가: `providers/<name>.py`에 `LLMProvider`(`stream_turn`) 구현 + `providers/__init__.py` 등록. 응답 원본은 `Message.raw`에 그대로 보관·재전송(Claude thinking, Gemini thought signature 등). 루프·도구·저장·UI는 그대로.
- **어댑터를 바꾸면 가짜 스트림 테스트만으로 끝내지 않는다.** 공급자마다 스트림 형식이 다르다(예: Gemini는 병렬 도구 호출을 같은 `index`로 보냄 → 실제 API에서만 드러났음). 실제 API로 **도구 2개 동시 호출 + 같은 대화 2턴째**까지 한 번 확인하고, 드러난 형식은 테스트 픽스처로 추가한다.
- `SYSTEM_PROMPT`(`agent/prompts.py`)에 날짜 등 바뀌는 값을 넣지 않는다 (프롬프트 캐시가 깨짐). 공용 파일이라 변경 시 리뷰 필요.
- 대화 기록은 append-only (`raw`의 thinking 블록 유효성). 저장된 메시지를 수정·삭제하는 기능을 만들지 않는다.
- **LLM 일시 오류**(한도 초과 429·5xx)는 루프가 글자를 보내기 전에만 대기 후 재시도한다(`AGENT_LLM_RETRIES`=2, retry-after 또는 4초→8초, 최대 20초). 오류 문구는 `app/agent/errors.py`에서 사용자용 한국어로 바꿔 SSE `error.message`로 보낸다 — 화면에 예외 이름을 노출하지 않는다.
- **비용 보호** (공개 API): IP당 10분 20회, 서버 전체 하루 500회, 대화당 메시지 80개, 턴당 출력 8000토큰, 요청당 6턴 (`CHAT_*`, `LLM_MAX_TOKENS`, `AGENT_MAX_TURNS`). 메모리 기준이라 재시작 시 초기화 — **Anthropic Console에서 월 사용 한도도 설정**한다.
- 대화가 길어져도 앞부분을 잘라 보내지 않는다 (기록 수정 → thinking 블록 무효·캐시 손실). 한도를 넘으면 409로 새 대화를 시작하게 한다.
- 품질 확인: `cd backend && .venv/bin/python -m evals.run_eval` — **실제 API 비용 발생**, 실행 전 사용자 확인. `--provider mock`은 무료(흐름만).

## 배포 & 환경변수
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

## Claude 작업 방식
- 세션 시작 시 훅이 브랜치·동기화 상태, 내 이슈, 열린 PR을 보여준다. main보다 뒤처져 있으면 먼저 `/sync`를 제안한다.
- 스킬:
  | 스킬 | 언제 |
  |---|---|
  | `/new-issue` | 칸반 카드(이슈) 만들기 |
  | `/start-task <이슈번호>` | 이슈 작업 시작 (assign + 브랜치/worktree) |
  | `/add-endpoint` | 기능에 API 추가 (계약 → backend → frontend api.ts → 테스트) |
  | `/add-page` | 새 화면 추가 (라우트 + 기능 폴더 + 사이드바 메뉴) |
  | `/add-agent-tool` | AI 에이전트에 도구 추가 (도구 파일 → 테스트 → eval 케이스) |
  | `/pr-check` | PR 전 충돌 검사 (git 충돌·같은 화면 경로·마이그레이션 번호·다른 PR과 겹침) |
  | `/sync` | main 반영 |
  | `/handoff` | 작업 마무리 (검증·셀프리뷰·PR `Closes #`) |
  | `/team-status` | 팀 현황 (이슈·PR·충돌 위험) |
  | `/deploy-status` | 배포 파이프라인·서비스 상태 확인 |
- PR 전에는 `reviewer` 서브에이전트로 셀프 리뷰.
- **다른 사람 PR의 충돌을 풀 때**는 그 브랜치에 main을 merge한다 (rebase·force push로 남의 기록을 바꾸지 않는다). 남의 기능 파일이 걸리면 선택지를 사용자에게 묻는다.
- 이슈 생성·push·PR 생성·수동 재배포는 사용자 확인 후. PR 머지는 사람이 한다. 공유 DB에 직접 SQL을 실행하지 않는다 (마이그레이션 파일 + 배포 파이프라인으로만).
