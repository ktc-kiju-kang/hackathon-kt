# 본선 시작 키트

> 10/14 주제 공개 → 10/15 00:00 개발 마감. 배정받은 팀 레포에 **첫 1시간 안에** 개발 환경·작업 규칙·제출 문서 뼈대를 깔기 위한 키트다.
> 결정: **로컬 우선** — 외부 서비스(Vercel·Render·Supabase) 없이 PC에서 실행하고 시험한다 (2026-10-08 팀 결정).

## 무엇이 들어가나
| 구분 | 내용 | 출처 |
|---|---|---|
| 프론트 | Next.js 16 + TS + Tailwind v4 + shadcn/ui + **KDS 2.0 토큰**, 공용 레이아웃·사이드바·PageHeader·ErrorLine·AI 라벨, `/agent`(AI 채팅), `/samples/*`(UI 예시), Vitest | 이 레포 그대로 |
| 백엔드 | FastAPI(라우터 자동 등록), AI 에이전트 엔진(Claude·Gemini·OpenAI 호환·**mock**), 사용량 한도, `/api/health`(`version`=git SHA), pytest 54개 | 이 레포 + 덮어쓰기 |
| DB | **SQLite** (`backend/data/app.db`), `database/migrations/*.sql` 서버 시작 시 자동 적용, 대화 저장 | 덮어쓰기 |
| 작업 규칙 | `CLAUDE.md`(채점 근거 규칙 포함), `.claude/` 규칙·스킬(`/new-issue`→`/start-task`→`/add-endpoint`→`/handoff`)·reviewer | 이 레포 + 덮어쓰기 |
| 제출 문서 | `README.md` + `docs/` 7개, `scripts/check-docs.py`, `docs/submission-guide.md` | `templates/submission/` |
| **파이프라인** | `make setup·dev·verify·serve·stop·status·e2e·submit-check`, `scripts/*.sh`, `e2e/`(배포 서버 대상 HTTP 시험), `scripts/e2e-report.py`(TC 결과 자동 기록), `docs/pipeline.md`(단계·게이트·시간표·장애 대응), 스킬 `/plan-topic`·`/submit` | 덮어쓰기 |
| PR 점수 | **PR Review** 워크플로(자동 점검 40점 코멘트, 비차단) + `scripts/pr_review_score.py`·테스트 — #80 (ktc-jehyuk-kim). 키트용 패치: venv 설치, `ty check app tests`, `e2e/`를 테스트로 인정 | 이 레포 + 패치 |
| CI | frontend·backend·docs·**e2e**(설치 → 격리 배포 → E2E) (`.github/workflows/ci.yml`), gitleaks | 덮어쓰기 |

빠지는 것: 이 레포의 주제 기능(trends·radar·product)과 데이터, Vercel·Render·Supabase 배포 설정, 칸반 자동화, evals, `deploy-status` 스킬.

## 쓰는 법 (10/14)
```sh
# 0. 배정 레포를 clone (사내 GHE, VPN 연결)
git clone <배정 레포 URL> ~/team-repo

# 1. 미리보기 → 내보내기 (이 레포 루트에서)
python3 templates/starter/export.py ~/team-repo --dry-run
python3 templates/starter/export.py ~/team-repo
```
- 대상에 **이미 있는 파일은 건너뛰고** 목록을 보여 준다 (주최 측이 넣어 둔 README 등). 내용을 비교해 직접 합치거나 `--force`로 덮어쓴다.
- `.gitignore`가 이미 있으면 덮어쓰지 않고 **빠진 줄만 덧붙인다** (`.env`·`app.db` 커밋 방지). `backend/.gitignore`도 따로 들어간다.
- `docs/security-policy.md`, `.github/ISSUE_TEMPLATE/**`(주최 측 제공)는 `--force`여도 건드리지 않는다.

```sh
# 2. 실행 확인
cd ~/team-repo
make setup && make verify && make serve   # 브라우저 http://localhost:3000 확인 후 make stop

# 3. 첫 커밋 (main 보호가 있으면 브랜치 → PR)
git switch -c chore/starter-kit && git add -A && git commit -m "chore: 시작 키트" && git push -u origin chore/starter-kit
```
4. 주제가 나오면 `/plan-topic <주제 원문>` → 기획 게이트 통과 후 `/new-issue`. 이후 단계는 `docs/pipeline.md` (개발 → `make e2e` → `/submit`).
5. 서비스 이름을 바꿀 곳: `frontend/src/app/layout.tsx`(title), `components/app-sidebar.tsx`(배너), `src/app/page.tsx`(홈), `backend/app/agent/prompts.py`(에이전트 역할), `features/chat/ChatView.tsx`(예시 질문).
6. AI 기능이 필요 없는 주제면 `/agent`를 메뉴에서 빼면 된다 (코드는 남겨도 무방). 주제에 맞는 기능은 `/add-endpoint`·`/add-page`로 추가.

## 사내 GHE에서 CI가 안 돌면
첫 push 뒤 Actions 탭을 확인한다. `actions/checkout` 등을 쓸 수 없어 CI가 시작하지 않으면, PR 전에 `CLAUDE.md` "명령"의 검증을 로컬에서 실행하고 결과를 PR 본문에 붙인다 (`/handoff`가 실행한다).

## 파이프라인 확인 (2026-10-08, 원격 저장소까지 흉내 낸 시뮬레이션)
내보내기 → `make setup` → 문서 채우기 → 테스트 이름에 TC ID → `make e2e` → 근거 커밋·push → `make submit-check`:
- `make verify` 9개 검사 PASS (gitleaks는 미설치 시 SKIP), `make serve` 스모크(버전 = HEAD) PASS, 같은 포트 재실행 거부, `make stop` 후 포트 해제
- `make e2e`: TC 6개 자동 기록(backend 4·e2e 2) → `e2e-test.md` 상태·근거·환경·요약 개수, `prd.md` REQ 3개 `계획 → 검증됨`, `docs/evidence/<실행>/`에 XML·로그·요약. 일부러 실패시킨 TC는 FAIL로 기록되고 `make e2e`가 실패로 끝남. 시험 후 작업 트리에는 문서·근거만 남음
- `make submit-check`: 정상이면 SHA 출력. 막는 경우 확인 — 커밋 안 된 변경, push 안 함, 근거 이후 코드 변경, 포맷 오류(verify --strict), dirty 상태 시험 결과는 근거로 안 씀

## 확인된 것 (2026-10-08, 빈 폴더로 내보내기)
- backend: ruff·ty 통과, pytest 54개 통과
- frontend: lint 통과, Vitest 16개 통과, build 성공 (`/`, `/agent`, `/samples/*`)
- 실제 실행: `/api/health` → `db: ok, llm: mock` / 대화 생성 → 메시지 → mock이 계산 도구 호출 → 다른 X-Client-Id는 404 → **서버 재시작 후에도 대화 4개 메시지 유지**
- 이미 있는 파일 건너뜀, `--force`, 주최 측 파일 보호, 재실행 시 변경 0개

## 관리
- 공용 코드(UI·에이전트·스킬)는 이 레포에서 고치면 다음 내보내기에 반영된다. 로컬 실행용으로 **바꿔야 하는 파일만** `overlay/`에 있다.
- `export.py`의 `PATCHES`는 원본 문자열을 찾아 바꾼다. 원본이 바뀌어 문자열이 없으면 내보내기가 **실패**한다 → CI `starter-kit` 잡이 PR마다 내보내기 + backend 시험을 돌려 잡는다.
