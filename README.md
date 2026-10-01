# KT 해커톤

프론트: https://hackathon-kt.vercel.app · API: https://hackathon-kt-api.onrender.com/api/docs

## 시작하기 (팀원 각자)
```bash
git clone https://github.com/ktc-kiju-kang/hackathon-kt.git && cd hackathon-kt

# frontend — http://localhost:3000
cd frontend && npm install && cp .env.example .env.local && npm run dev

# backend — http://localhost:8000/api/docs  (Supabase 키는 팀 채널에서 받아 .env에)
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
cp .env.example .env && .venv/bin/fastapi dev app/main.py

claude   # 세션 시작 시 내 이슈·열린 PR 표시
```

> Claude가 칸반 카드를 옮기려면 gh에 `project` 권한이 필요합니다(1회):
> `gh auth refresh -h github.com -s project`

## 배포 최초 설정 (1회, 관리자)
- **Vercel**: New Project → `ktc-kiju-kang/hackathon-kt` → **Root Directory `frontend`** → 환경변수 `NEXT_PUBLIC_API_BASE_URL=https://hackathon-kt-api.onrender.com` (Production·Preview 모두). 없으면 배포 사이트가 조용히 mock으로 동작한다.
- **Render**: `render.yaml` Blueprint (연결됨). 대시보드에서 `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` 입력.
- **Supabase**: 프로젝트 1개 생성 → 키를 Render와 각자 `backend/.env`에.

## 흐름 (기능 단위)
1. [칸반](https://github.com/users/ktc-kiju-kang/projects/1)에서 Todo 카드 선택 또는 `/new-issue`로 생성
2. `/start-task <이슈번호>` → 본인 assign + `feat/<번호>-<설명>` 브랜치
3. 기능 파일만 만들어 구현 (`/add-endpoint`로 계약 → backend → frontend)
4. `/handoff` → `Closes #번호` PR → CI 통과 + 리뷰 1명 → 머지 → 카드 Done, 자동 배포

## 구조
```
frontend/                 Next.js + TS + Tailwind + shadcn/ui   → Vercel
  src/app/<route>/          화면
  src/features/<feature>/   기능별 컴포넌트 + API client(api.ts)
backend/                  FastAPI                               → Render
  app/routers|services|schemas/<feature>.py
database/                 Supabase 마이그레이션·seed
docs/contracts/           기능별 API 계약
docs/decisions/           기술 결정 기록(ADR)
.claude/                  팀 공용 Claude 설정·스킬·reviewer
.github/                  이슈/PR 템플릿, CI
scripts/                  new-worktree / sync / session-context
render.yaml               Render 배포
.env.example              전체 환경변수 목록
```
