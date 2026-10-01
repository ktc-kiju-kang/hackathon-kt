# KT 해커톤

🌐 웹: https://kiju-kang.github.io/hackathon-kt/ · API: https://hackathon-kt-api.onrender.com/api/docs

## 시작하기 (팀원 각자)
```bash
git clone https://github.com/kiju-kang/hackathon-kt.git && cd hackathon-kt
cd web && npm install && npm run dev                      # 웹: http://localhost:5173
cd api && python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/fastapi dev app/main.py                         # API: http://localhost:8000/api/docs
claude                        # 세션 시작 시 팀 현황 자동 표시
/start-task a T-001 setup     # 작업 시작
```

## 구조
```
CLAUDE.md                 팀 공용 규칙 (Claude가 자동으로 읽음)
.claude/
  settings.json           공용 권한 + SessionStart 훅
  commands/               /start-task /sync /handoff /team-status
  agents/reviewer.md      PR 전 셀프 리뷰 서브에이전트
docs/
  TEAM.md                 멤버·역할·소유 영역
  CONTRACTS.md            API/타입/스키마 계약 (단일 진실)
  decisions/              기술 결정 기록(ADR)
  status/<member>.md      멤버별 현황 (본인 파일만 수정)
tasks/T-xxx-*.md          작업당 1파일
scripts/                  new-worktree / sync / session-context
web/                      프론트엔드 (Vite + React + TS)
api/                      백엔드 (FastAPI)
.github/workflows/        CI(lint+build) / Pages 배포
```

## 흐름
`/start-task` → 구현 → `/sync` → `/handoff` → PR → 리뷰 1명 → squash merge
