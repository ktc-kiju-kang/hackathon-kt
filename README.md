# KT 해커톤 본선 준비 — 시작 키트

2026-10-14~15 본선(AID-X Pro-code)에서 **배정받은 팀 레포에 첫 1시간 안에 깔** 개발 환경·작업 규칙·제출 문서 뼈대.
이 레포 자체가 키트와 같은 구조로 돌아간다 (서버 없이 로컬 PC에서만: SQLite, LLM 키 없으면 mock).

## 바로 쓰기
```sh
make setup    # 설치 (Node 20+, Python 3.11+)
make dev      # 개발 서버 http://localhost:3000 · API http://localhost:8000/api/docs
make verify   # 검사 전부 (lint·type·test·build)
make serve    # 로컬 배포 (프로덕션 빌드 + 스모크) / make stop
make e2e      # 시험 + 격리 배포 E2E
make help     # 명령 전부
```

## 본선 당일
```sh
git clone <배정 레포> ~/team-repo
python3 templates/starter/export.py ~/team-repo --dry-run   # 미리보기
python3 templates/starter/export.py ~/team-repo             # 키트 깔기
```
이후 순서: `/plan-topic`(기획) → Issue → 각자 `/start-task` → 구현 → **`make ship`**(검사·시험·PR·AI 리뷰·자동 머지) → `make record`(시험 기록) → `make submit-check`(포털에 넣을 SHA).
- 단계·게이트·시간표: [docs/pipeline.md](docs/pipeline.md)
- 키트 내용·리허설 결과: [templates/starter/README.md](templates/starter/README.md)
- 채점 기준·제출 문서 8개: [templates/submission/GUIDE.md](templates/submission/GUIDE.md)

## 구성
| 경로 | 내용 |
|---|---|
| `frontend/` | Next.js 16 + TS + Tailwind v4 + shadcn/ui + KDS 2.0 토큰, `/agent`(AI 채팅), `/samples/*` |
| `backend/` | FastAPI(라우터 자동 등록), AI 에이전트 엔진(Claude·Gemini·OpenAI 호환·mock), SQLite |
| `e2e/` · `scripts/` · `Makefile` | 파이프라인 (setup·dev·verify·serve·e2e·ship·record·submit-check) |
| `.claude/` | 팀 규칙·스킬·reviewer (Claude Code) |
| `templates/` | 키트 내보내기(`starter/`), 제출 문서 8개 템플릿(`submission/`) |

이전 주제(KT Group AI Opportunity Radar)와 클라우드 배포(Vercel·Render·Supabase)는 2026-10-08에 정리했다 — git 이력(`fdea432` 이전)에 남아 있다.
