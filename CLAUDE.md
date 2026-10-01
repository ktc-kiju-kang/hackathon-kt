# KT 해커톤 프로젝트

> 3명이 동시에 Claude Code로 작업하는 레포. **이 파일은 팀 공용 규칙**이며, 개인 메모는 `CLAUDE.local.md`(gitignore됨)에 쓴다.
> 저장소는 **공개**다. 키·토큰·개인정보는 절대 커밋하지 않는다.

## 개요
- 주제: _TBD_
- 저장소: https://github.com/ktc-kiju-kang/hackathon-kt
- 칸반: https://github.com/users/ktc-kiju-kang/projects/1 (GitHub Projects "KT 해커톤") — 카드 = 이슈
- 프론트(배포): https://hackathon-kt.vercel.app (Vercel, PR마다 프리뷰 URL)
- API(배포): https://hackathon-kt-api.onrender.com/api/docs
- DB: Supabase (팀 공유 클라우드 프로젝트 1개)

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
  src/components/                  공용 컴포넌트, providers.tsx
  src/lib/api-client.ts            공용 HTTP 클라이언트(request, isMock)
  src/app/layout.tsx, page.tsx     공용 (최소 수정)
backend/                         FastAPI
  app/routers/<feature>.py         엔드포인트 (자동 등록) — 기능 담당자
  app/services/<feature>.py        비즈니스 로직·DB 접근 — 기능 담당자
  app/schemas/<feature>.py         Pydantic 요청/응답 모델 — 기능 담당자
  app/main.py, config.py, db.py    공용 (main.py는 수정 불필요)
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
3. **동시에 여러 이슈는 worktree로:** `scripts/new-worktree.sh <이슈번호> <설명>`
4. **계약 우선:** 다른 기능·화면이 쓰는 API는 `docs/contracts/<feature>.md`에 먼저 정의한다. 남의 기능 계약을 바꾸면 그 담당자를 PR 리뷰어로 지정한다.
5. **공용 파일은 최소한으로, 작게 고친다:** `layout.tsx`, `src/app/page.tsx`, `api-client.ts`, `components/`, `config.py`, `db.py`, `requirements*.txt`, `package.json`, 루트 설정. 큰 변경은 별도 PR로 먼저 머지한다.
6. **남의 기능 파일은 직접 고치지 않는다.** 필요하면 담당자에게 요청하거나, 사용자 확인 후 수정하고 담당자를 리뷰어로 지정한다.
7. **DB 마이그레이션은 공유 DB에 바로 반영된다.** 번호는 머지 직전에 확정, drop/rename 같은 파괴적 변경은 팀에 먼저 알린다.
8. **작게, 자주 머지.** 작업 시작 전과 PR 전에 `scripts/sync.sh`로 main 반영.
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
- effect 본문에서 setState를 동기 호출하지 않는다 (lint 에러). 비동기 콜백(`.then`)에서 호출한다.

### backend
- 기능 = `routers/<feature>.py` + `services/<feature>.py` + `schemas/<feature>.py`.
  - `router = APIRouter(prefix="/<feature>", tags=["<feature>"])`를 정의하면 자동 등록 → `/api/<feature>/...`
  - router는 얇게(검증·응답), 로직·DB 접근은 service에. `response_model` 항상 지정.
- DB는 `app.db.get_supabase()`로 service에서만 접근. 설정·비밀값은 `app/config.py`의 `Settings`로만 읽는다.
- 기능마다 `tests/test_<feature>.py`에 최소 1개 테스트. DB가 필요한 테스트는 service를 monkeypatch해 DB 없이 돌게 한다 (CI에는 DB 없음).

## 배포 & 환경변수
| | 트리거 | 환경변수 |
|---|---|---|
| frontend → Vercel | main 머지 시 프로덕션, PR마다 프리뷰 URL | Vercel 프로젝트 환경변수 `NEXT_PUBLIC_API_BASE_URL`(= Render URL) |
| backend → Render (free, singapore) | main 머지 + CI 통과 | `render.yaml`의 `envVars`. 비밀값(`SUPABASE_*`)은 `sync: false`, Render 대시보드에서 입력 |
| database → Supabase | 수동 (SQL Editor / psql) | — |

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
  | `/sync` | main 반영 |
  | `/handoff` | 작업 마무리 (검증·셀프리뷰·PR `Closes #`) |
  | `/team-status` | 팀 현황 (이슈·PR·충돌 위험) |
  | `/deploy-status` | 배포(Vercel/Render) 상태 확인 |
- PR 전에는 `reviewer` 서브에이전트로 셀프 리뷰.
- 이슈 생성·push·PR 생성·DB 마이그레이션 적용은 사용자 확인 후. PR 머지는 사람이 한다.
