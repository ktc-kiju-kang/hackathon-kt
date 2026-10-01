# KT 해커톤 프로젝트

> 3명이 동시에 Claude Code로 작업하는 레포. **이 파일은 팀 공용 규칙**이며, 개인 메모는 `CLAUDE.local.md`(gitignore됨)에 쓴다.
> 저장소는 **공개**다. 키·토큰·개인정보는 절대 커밋하지 않는다.

## 개요
- 주제: _TBD_
- 저장소: https://github.com/kiju-kang/hackathon-kt
- 웹(배포): https://kiju-kang.github.io/hackathon-kt/
- API(배포): https://hackathon-kt-api.onrender.com/api/docs

## 구조
```
web/        프론트엔드 — Vite + React + TS + Tailwind v4 + shadcn/ui (owner: a)
api/        백엔드 — FastAPI (owner: b)
docs/       TEAM(멤버·소유) / CONTRACTS(API 계약) / decisions(ADR) / status(멤버별 현황)
tasks/      작업당 1파일 (T-xxx-*.md)
scripts/    new-worktree / sync / session-context
.claude/    공용 설정, 스킬, reviewer 에이전트
render.yaml Render 배포 Blueprint
```

## 명령
| | web (`cd web`) | api (`cd api`) |
|---|---|---|
| 셋업 | `npm install` | `python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt` |
| 실행 | `npm run dev` → :5173 | `.venv/bin/fastapi dev app/main.py` → :8000 (`/api/docs`) |
| 검증 | `npm run lint && npm run build` | `.venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/pytest` |

**PR 전 변경한 쪽의 검증 명령을 반드시 통과시킨다.** CI(`web`, `api` 잡)가 동일하게 실행한다.

## 협업 규칙 (Claude도 반드시 따를 것)
1. **main 직접 커밋·push 금지.** main은 보호됨: PR + CI(`web`, `api`) 통과 + 1명 승인 필요.
   - 브랜치명: `<member>/<task-id>-<짧은설명>` (예: `a/T-003-login-page`)
   - 머지된 브랜치는 GitHub에서 자동 삭제된다.
2. **동시에 여러 작업은 git worktree로:** `scripts/new-worktree.sh <member> <task-id> <설명>`
3. **계약 우선:** 멤버 간 경계(API·타입·스키마)는 `docs/CONTRACTS.md`가 단일 진실. 계약 변경은 작은 PR로 먼저 머지 후 구현.
4. **공용 파일 동시 편집 금지:**
   - 진행상황 → `docs/status/<member>.md` (본인 파일만)
   - 작업 → `tasks/T-xxx-*.md` (작업당 1파일, owner만 수정. 번호 대역 a=001~299, b=300~599, c=600~899)
5. **작게, 자주 머지.** 작업 시작 전과 PR 전에 `scripts/sync.sh`로 main 반영.
6. 커밋: `<type>(<scope>): <요약>` — type: feat/fix/refactor/docs/chore/test, scope: web/api/docs/ci 등
7. 다른 멤버 소유 영역, `docs/CONTRACTS.md`, 루트 설정(`CLAUDE.md`, `.claude/`, `render.yaml`, `.github/`)을 바꿔야 하면 **먼저 사용자에게 확인**하고 PR에 해당 owner 리뷰를 요청한다.

## 코드 규칙

### web
- UI는 shadcn 컴포넌트 우선: `npx shadcn@latest add <이름>` → `src/components/ui/`
- `src/components/ui/`는 생성 코드. 직접 수정 최소화, 조합 컴포넌트는 `src/components/`에 둔다.
- import는 `@/` 별칭, 클래스 병합은 `cn()` (`@/lib/utils`), 아이콘은 `lucide-react`
- 색상은 테마 토큰(`bg-background`, `text-muted-foreground` 등)만 사용. 테마는 `src/index.css`. 다크모드는 시스템 설정 연동(`.dark`).
- 알림은 `sonner`의 `toast`.
- **API 호출은 `src/api/client.ts`에만.** 타입은 `api/app/schemas.py`와 맞춘다. 백엔드 미구현 엔드포인트는 mock을 먼저 둔다.

### api
- 라우터는 `app/routers/<도메인>.py`에 만들고 `app/main.py`에서 `prefix="/api"`로 등록.
- 요청/응답 모델은 `app/schemas.py` (Pydantic). `response_model`을 항상 지정한다.
- 설정·비밀값은 `app/config.py`의 `Settings`(환경변수)로만 읽는다.
- 새 엔드포인트마다 `tests/`에 최소 1개 테스트.

## 배포 & 환경변수
| | 트리거 | 환경변수 |
|---|---|---|
| web → GitHub Pages | main에 `web/**` 변경 머지 | 빌드 시 저장소 Actions 변수(`VITE_API_BASE_URL` = Render URL) 주입. 변경은 관리자 권한 필요 |
| api → Render (free, singapore) | main 머지 + CI 통과 | `render.yaml`의 `envVars`. 비밀값은 `sync: false`로 선언하고 Render 대시보드에서 입력 |

- 로컬: `web/.env`, `api/.env` (커밋 금지). 새 키는 각 `.env.example`에 이름만 추가.
- `VITE_*` 변수는 브라우저 번들에 그대로 노출된다. 비밀값을 넣지 말 것.
- Render free 플랜은 15분 미사용 시 잠든다(첫 요청 ~1분). 데모 직전에 `/api/health`를 호출해 깨운다.

## Claude 작업 방식
- 세션 시작 시 훅이 브랜치·동기화 상태와 팀원 현황을 보여준다. main보다 뒤처져 있으면 먼저 `/sync`를 제안한다.
- 스킬:
  | 스킬 | 언제 |
  |---|---|
  | `/start-task` | 작업 시작 (task 파일 + 브랜치/worktree) |
  | `/add-endpoint` | API 기능 추가 (계약 → api → web client → 테스트) |
  | `/sync` | main 반영 |
  | `/handoff` | 작업 마무리 (검증·셀프리뷰·status·PR) |
  | `/team-status` | 팀 전체 현황 |
  | `/deploy-status` | 배포(Pages/Render) 상태 확인 |
- PR 전에는 `reviewer` 서브에이전트로 셀프 리뷰.
- push·PR 생성은 사용자 확인 후. PR 머지는 사람이 한다.
