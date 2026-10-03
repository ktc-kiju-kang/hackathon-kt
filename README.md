# KT 해커톤

프론트: https://hackathon-kt.vercel.app · API: https://hackathon-kt-api.onrender.com/api/docs

## 시작하기 (팀원 각자)
```bash
git clone https://github.com/ktc-kiju-kang/hackathon-kt.git && cd hackathon-kt

# frontend — http://localhost:3000
cd frontend && npm install && cp .env.example .env.local && npm run dev

# backend — http://localhost:8000/api/docs  (SUPABASE_URL·SUPABASE_SERVICE_ROLE_KEY는 팀원에게 안전한 경로로 받아 .env에)
# uv 필요: brew install uv (또는 pip install uv)
cd backend && uv venv && uv pip install -r requirements-dev.txt
cp .env.example .env && .venv/bin/fastapi dev app/main.py

# AI 기능(/agent·/radar·/product): backend/.env에 GEMINI_API_KEY(무료, 하루 한도 작음) 또는 ANTHROPIC_API_KEY, 없으면 mock LLM
# 키가 있어도 mock으로 띄우려면: LLM_PROVIDER=mock .venv/bin/fastapi dev app/main.py

claude   # 세션 시작 시 내 이슈·열린 PR 표시
```

> `/start-task`가 칸반 카드를 In Progress로 옮기려면 gh에 `project` 권한이 필요합니다(1회):
> `gh auth refresh -h github.com -s project`

## 배포 최초 설정 (1회, 관리자)
- **Vercel**: New Project → `ktc-kiju-kang/hackathon-kt` → **Root Directory `frontend`** → 환경변수 `NEXT_PUBLIC_API_BASE_URL=https://hackathon-kt-api.onrender.com` (Production·Preview 모두). 없으면 배포 사이트가 조용히 mock으로 동작한다.
- **Render**: 서비스 연결 저장소 `ktc-kiju-kang/hackathon-kt`, Root Directory `backend`. **Settings → Auto-Deploy: Off**, Deploy Hook URL 복사. 대시보드에서 `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` 입력.
- **Supabase** (생성됨: `atirjbxwroqkbopnqybz`, Singapore):
  - `SUPABASE_URL` = `https://atirjbxwroqkbopnqybz.supabase.co`
  - `SUPABASE_SERVICE_ROLE_KEY` = Project Settings → API Keys → **Legacy API keys의 `service_role`** (`eyJ…`) → Render와 각자 `backend/.env`에
  - `SUPABASE_DB_URL` = Connect → Direct → **Session pooler** (`postgresql://postgres.atirjbxwroqkbopnqybz:[비밀번호]@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres`, 특수문자는 URL 인코딩). GitHub Actions는 IPv6 direct 연결 불가
- 설정 확인: `scripts/smoke.sh` — 모두 ✅ (특히 `DB 연결 ok`)면 끝
- **GitHub Secrets** (Settings → Environments → **production** → Environment secrets):

  | Secret | 값 |
  |---|---|
  | `RENDER_DEPLOY_HOOK_URL` | Render Deploy Hook URL |
  | `VERCEL_TOKEN` | vercel.com/account/tokens 에서 생성 |
  | `VERCEL_ORG_ID` | Vercel 팀(개인 계정도 팀) **Settings → General → Team ID** (`team_…`). Account의 Vercel ID 아님 |
  | `VERCEL_PROJECT_ID` | Vercel 프로젝트 Settings → General → Project ID (둘 다 `cd frontend && npx vercel link` 후 `.vercel/project.json`으로도 확인) |
  | `SUPABASE_DB_URL` | Supabase Session pooler 연결 문자열 (비밀번호 포함) |

배포 흐름: main 머지 → CI → Deploy 워크플로(마이그레이션 → backend → frontend → 스모크 테스트). 상세는 `docs/deploy.md`.

## 화면
| 경로 | 내용 | 기능 폴더 |
|---|---|---|
| `/` | 홈 (API·DB 상태) | `features/health` |
| `/trends` | AI 활용 트렌드 (OpenAI Signals 지표 대시보드) | `features/trends` ↔ `/api/trends` |
| `/radar` | Opportunity Radar (그룹사 선택 → 근거 있는 AI 사업 기회) | `features/radar` ↔ `/api/radar` |
| `/product` | Product Generator (기회 → Product Card·PoC, Markdown 내보내기) | `features/product` ↔ `/api/product` |
| `/agent` | AI 에이전트 (스트리밍 채팅 + 도구) | `features/chat` ↔ `/api/chat` |
| `/samples/*` | UI 샘플: 에디터·테이블·복합 화면·모달 | `features/samples` |

새 화면은 `/add-page` (라우트 + 기능 폴더 + 사이드바 메뉴).

## 흐름 (기능 단위)
1. [칸반](https://github.com/users/ktc-kiju-kang/projects/1)에서 Todo 카드 선택 또는 `/new-issue`로 생성
2. `/start-task <이슈번호>` → 본인 assign + `feat/<번호>-<설명>` 브랜치
3. 기능 파일만 만들어 구현 (`/add-endpoint`로 계약 → backend → frontend)
4. `/handoff` → 충돌 검사(`/pr-check`) → `Closes #번호` PR → CI 통과 → 작성자가 머지 (공용 파일·계약·마이그레이션 변경은 리뷰 요청 후) → 카드 Done, 자동 배포

## 구조
```
frontend/                 Next.js + TS + Tailwind + shadcn/ui   → Vercel
  src/app/<route>/          화면
  src/features/<feature>/   기능별 컴포넌트 + API client(api.ts)
backend/                  FastAPI                               → Render
  app/routers|services|schemas/<feature>.py   (목표: app/features/<feature>/ — docs/decisions/0007)
  app/agent/                AI 에이전트 (LLM 어댑터·도구·루프·구조화 출력), evals/ 평가
  data/                     공개 정적 데이터 (OpenAI Signals CSV, 그룹사 JSON)
database/                 Supabase 마이그레이션·seed
docs/contracts/           기능별 API 계약
docs/decisions/           기술 결정 기록(ADR)
.claude/                  팀 공용 Claude 설정·스킬·reviewer
.github/                  이슈/PR 템플릿, CI
scripts/                  new-worktree / sync / check-conflicts / migrate / smoke / session-context
render.yaml               Render 배포
.env.example              전체 환경변수 목록
```
