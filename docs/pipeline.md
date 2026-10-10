# 파이프라인 — 기획부터 로컬 배포·제출까지

> 단계마다 **산출물**과 **통과 기준(게이트)** 이 있다. 게이트를 통과하지 못하면 다음 단계로 가지 않는다.
> 입구는 `make` 하나다 (`make help`). 모든 명령은 로컬에서 돌고, CI가 있으면 같은 검사를 한 번 더 한다.

## 한눈에
```
기획 ─▶ 설계 ─▶ 개발(Issue마다 반복, 3명 동시) ──────────────────▶ 시험 기록 ─▶ 제출
/plan-topic  /add-endpoint  /start-task → 구현·시험 → make ship(자동 머지)   make record   make submit-check
                                             └ 각자 PC: make dev / make serve (로컬 배포)
```

| 단계 | 산출물 | 명령·스킬 | 게이트 (통과 기준) |
|---|---|---|---|
| 0. 준비 | 키트가 깔린 배정 레포, 의존성 | `export.py`(이 레포 밖에서) → `make setup` | `make verify` 전부 PASS |
| 1. 기획 | `project-brief.md`, `prd.md`(REQ·AC), TC 시나리오, SEC 매핑, Issue 분할안 | `/plan-topic` (역할 분담: [requirements-flow.md](requirements-flow.md)) | `make docs` 오류 0 · 모든 REQ에 AC, 모든 AC에 TC · **팀 합의** |
| 2. 설계 | `docs/contracts/<feature>.md`, `arch.md`(구성·데이터·API), 계약의 테이블 SQL 초안 | `/add-endpoint` 1단계(계약), ADR(`docs/decisions/`) | 화면·API 담당이 계약에 동의 |
| 3. 개발·자동 머지 | 브랜치·코드·테스트(이름에 TC ID), 문서 갱신 → PR·AI 리뷰·머지 | `/start-task` → 구현 → `/handoff` = **`make ship`** | ship이 전부 확인: verify PASS · 충돌 ❌ 없음 · e2e 전체 PASS · AI 리뷰 차단 0·높음 0·42/60 이상 · CI 통과 → squash 머지 |
| 4. 통합·로컬 배포 | main 최신 코드가 프로덕션 빌드로 떠 있음 | `make serve` / `make status` / `make stop` | 스모크 PASS (health ok·db ok·**버전 = HEAD**·주요 화면 200) |
| 5. 시험 기록 | `e2e-test.md` 상태·근거, `prd.md` REQ 상태, `docs/evidence/<실행>/` | 기록 담당이 **`make record`** (main에서 e2e → 기록 파일만 담은 PR 자동 머지) | 전체 PASS, 커밋된 코드로 실행. 기능 PR에는 기록을 넣지 않는다 (충돌 방지) |
| 6. 제출 | 포털에 40자 SHA, 발표자료 | `make submit-check` → `/submit` | 깨끗한 트리 · origin/main = HEAD · `verify --strict` · 근거 이후 코드 변경 없음 |

## 각 명령이 하는 일
| 명령 | 내용 |
|---|---|
| `make setup` | Node 20+·Python 3.11+ 확인 → backend `.venv` + 의존성 → `npm ci` → `.env` 없으면 생성 (여러 번 실행해도 됨) |
| `make dev` | 개발 서버 (핫 리로드) api :8000 + web :3000 — **docker compose**(`compose.yaml` + `compose.dev.yaml`, 소스 마운트), Ctrl+C로 컨테이너까지 종료. docker 없이 `NATIVE=1 make dev` |
| `make verify` | ruff·ty·pytest·e2e lint·eslint·vitest·next build(격리 폴더)·문서 검사·(있으면) gitleaks 커밋 이력. 키트 스크립트 자체 시험(`scripts/test_*.py`)은 `scripts/`를 고친 브랜치에서만 — 팀 레포 CI `docs` 잡과 키트 원본 레포는 항상 돌린다 (ship마다 30초 절약). 하나가 실패해도 끝까지 돌고 요약, 로그 `.run/verify/`. `make serve` 중에 돌려도 된다 |
| `make serve` | **로컬 배포**: docker compose로 프로덕션 빌드 → api(`fastapi run`) + web(`next start`) 백그라운드(이 PC에서만, 127.0.0.1) → health·화면 스모크. 실패하면 스스로 내린다. 로그 `docker compose logs`. DB는 compose의 PostgreSQL(`127.0.0.1:55432`, volume `pgdata`), LLM 키는 `backend/.env`를 앱이 직접 읽는다. docker 없이 `NATIVE=1 make serve`(로그 `.run/`) |
| `make e2e` | ① backend pytest·frontend vitest ② **격리 로컬 배포**(포트 18000·13000대 — 체크아웃 경로마다 다른 번호라 같은 PC의 worktree 둘이 동시에 돌려도 안 겹침·새 DB·mock LLM)에 `e2e/` 시험 ③ TC별 결과를 `e2e-test.md`·`prd.md`에 기록, 근거(JUnit XML·로그·요약)를 `docs/evidence/`에 저장. `make serve`로 떠 있는 서버와 DB·빌드를 건드리지 않는다 |
| `make ship` | 작업 브랜치 → main. ① main merge + push·**초안 PR**(CI가 로컬 검사와 나란히 돌게) ② verify ③ 충돌 검사 ④ e2e(확인만, 기록 되돌림) ⑤ PR 본문 갱신·초안 해제(`Closes #` — 이미 닫힌 Issue의 후속 PR이면 `Refs #`라 칸반 카드가 Done에 남는다. PR 점수의 '이슈 연결'은 4/6, 확인 결과 자동 기록. Issue 본문 `- 머지 조건: #N`이 완료로 닫히지 않았으면 그 이유를 ⚠️로 적는다 — `docs/requirements-flow.md` 2절) ⑥ AI 리뷰(`claude -p` + reviewer 지침 → PR 본문 "AI 리뷰" 블록, PR 점수 60점 형식. 같은 PR 재리뷰는 이전 지적의 해결 여부부터 판정하고, 새 `높음`은 이번 변경에서 생긴 것만 머지를 막는다 — 수렴 규칙) ⑦ Issue 근거 댓글 — 머지 조건이 안 풀렸으면 여기서 멈춘다(`SHIP_NO_MERGE=1`이면 경고만). 루프 자동 머지(`TICKET_LOOP_MERGE=1`)는 테이블 초안 계약이 바뀌었거나 새 마이그레이션이 머지된 계약 초안과 다르면(`scripts/migration_draft.py`) 사람이 머지한다 ⑧ CI 대기(잠금 밖에서) → 머지 잠금 → main이 바뀌었으면 다시 반영·verify·CI → squash 머지 ⑨ main 확인(머지된 트리가 ②에서 검사한 트리와 같으면 verify 생략). 어느 단계든 기준 미달이면 멈춘다. 검사가 실패하면 PR은 초안인 채 남고(칸반 카드는 PR 연결로 In Review에 간다 — 고치는 중이라는 뜻), 고친 뒤 `make ship`이 같은 PR을 이어 쓴다. 초안 PR이 없는 레포(GitHub Free 비공개)는 제목 `WIP: `로 대신한다 |
| `make claims` | Issue 선점 목록: 번호·선점자·마지막 활동(작업 브랜치 커밋)·24시간 넘게 멈춘 것 ⚠️. 선점 = GitHub `claim/<번호>` 브랜치(원자적 생성). `/start-task`가 잡고, ship이 시작 전에 확인(없으면 잡음)·머지 후 지운다 |
| `make audit` | 보안 공통 점검: gitleaks(비밀값)·`npm audit --omit=dev`(frontend 운영 의존성)·`pip-audit`(backend) → `.run/audit/`, `security-compliance.md` 4절에 결과·시각·SHA. high 이상·비밀값이 있으면 1 — 의존성 변경은 `chore/deps-<이름>` 단독 PR |
| `make record` | main에서 e2e → AI 활용 기록(`development.md` 3절, 머지된 PR의 AI 리뷰 블록에서 `scripts/dev_log.py`) → `docs/record-<시각>` 브랜치에 기록 파일만 커밋 → ship(리뷰 생략, 기록 파일만 허용) |
| `make submit-check` | 제출 전 4가지 확인 → 포털에 넣을 SHA 출력. 근거는 **전체 PASS**여야 하고, 근거 이후 바뀐 것이 문서(`docs/`·`*.md`)뿐이어야 한다 |

## 시험과 TC 연결 규칙
- 테스트 이름에 TC ID를 넣으면 결과가 자동 기록된다. pytest `def test_tc_01_3_other_user_is_hidden`, vitest `it('TC-02-1 빈 입력이면 저장이 꺼진다')`.
- 어디에 쓰나: 로직·API·권한 → `backend/tests/` (빠름, DB는 테스트마다 새 파일) · 사용자 흐름(저장 → 재조회, 화면 응답) → `e2e/` (실제 배포에 HTTP) · 화면 로직 → `frontend/src/**/*.test.ts`.
- 같은 TC에 테스트가 여럿이면 하나라도 실패 → FAIL. 테스트가 없는 TC(수동 확인)는 자동으로 바꾸지 않는다 → 직접 실행하고 `e2e-test.md`에 명령·결과를 적는다.
- `prd.md` REQ 상태는 `make e2e`가 바꾼다: 그 REQ의 TC가 전부 PASS → `검증됨`, 일부만 → `구현됨-미검증`.
- 실제 LLM 결과 확인이 필요한 TC는 `E2E_LLM_PROVIDER=anthropic make e2e` (비용 발생, 사용자 확인 후).

## 하루 시간표 (10/14 주제 공개 → 10/15 00:00 마감)
| 시각 | 할 일 | 게이트 |
|---|---|---|
| 공개 직후 ~1h | A: 키트 내보내기 → `make setup`·`make verify` → 첫 커밋 ship / B·C: 주제 분석·`/plan-topic` | 기획 게이트 |
| ~2h | 계약·arch 초안(작은 PR로 ship), REQ별 Issue 생성·배정 (REQ 하나 = Issue 하나 = 한 사람, 기능 폴더가 겹치지 않게) / 공용 파일·의존성 변경은 이때 먼저 단독 PR로 | 설계 게이트 |
| ~20:00 | 개발 반복: 셋이 각자 `/start-task` → 시험부터 → 구현 → `make ship`. 반나절 넘는 브랜치 금지. **기록 담당(A)이 2~3시간마다 `make record`** | ship 게이트 |
| 20:00 | **기능 동결.** 새 REQ 금지, 미완성 REQ는 `제외(이유)` 또는 `구현됨-미검증`으로 정직하게 | — |
| 20:00~22:00 | 버그 수정, 문서 8개 채우기, 보안 준수표, AI 활용 기록 정리 | `make docs` 오류 0 |
| 22:00 | 기록 담당이 `make record` | 전체 PASS |
| 22:30 | `make submit-check` → 포털에 SHA 제출, 발표자료 업로드 | 제출 게이트 |
| ~23:30 | 여유 (재제출이 필요하면 고친 뒤 `make e2e` → `make submit-check` 다시) | — |

## 문제가 생기면
| 증상 | 할 일 |
|---|---|
| "docker가 없습니다"·"Docker가 꺼져 있습니다" | Docker Desktop 설치·실행. 급하면 `NATIVE=1 make dev` / `NATIVE=1 make serve` |
| docker 빌드가 의존성 변경을 못 따라감 | `make stop && make serve` (항상 `--build`). 그래도 이상하면 `docker compose build --no-cache` |
| `make serve` "포트 사용 중" | `make stop`. 다른 프로그램이면 `API_PORT=8100 WEB_PORT=3100 make serve` |
| 스모크 `version != HEAD` | 서버가 예전 코드. `make stop && make serve` |
| `make e2e` 배포 실패 | `.run/e2e/serve.log`, `.run/e2e-serve/*.log` |
| 머지 후 main이 깨짐 | 고치는 데 10분 이상이면 `git revert <머지 커밋>` → PR → 머지. 제출 마감 직전에는 되돌리기가 기본 |
| LLM 한도·장애 | mock으로도 화면·흐름이 동작한다. 발표에서는 녹화·캡처로 |
| DB가 꼬임 (로컬) | `make db-reset && make serve` (데이터 삭제 → 마이그레이션이 처음부터 다시 적용) |
| worktree 두 곳에서 `make dev`·`serve` "포트 55432(db) 사용 중" | 각 worktree가 자기 db를 띄운다. 두 번째는 `DB_PORT=55433` + 그 worktree `backend/.env`의 `DATABASE_URL`을 55433으로 (`make verify`·`e2e`는 첫 db를 같이 써도 schema로 격리돼 괜찮다) |
| "PostgreSQL에 접속할 수 없습니다" | Docker Desktop 실행 → `make db`. 포트 55432를 다른 프로그램이 쓰면 `DB_PORT=55433` + `backend/.env`의 `DATABASE_URL`도 같은 포트로 |
| CI가 안 돎 (사내 GHE) | 워크플로 파일이 없으면 ship이 "CI 없음"으로 보고 로컬 verify 결과로 진행한다. 워크플로는 있는데 Actions가 꺼져 있으면 "CI 체크가 생기지 않음"으로 멈춤 → `SHIP_NO_CI=1 make ship` |
| ship "머지 대기 중" | 다른 사람이 머지 중 — 기다린다. 15분 넘은 잠금은 자동으로 가져온다. 확인: `make lock-status` |
| start-task·ship "○○ 님이 이미 잡았습니다" | 그 Issue는 다른 사람 담당 — 다른 Issue를 고른다. 주인이 손을 뗐으면 본인이 `make release ISSUE=<번호>`, 연락이 안 되면 합의 후 `scripts/claim.sh release <번호> --force` |
| ship "머지 조건이 풀리지 않아" | 역할 분담의 FE 티켓이 같은 REQ의 BE보다 먼저 끝났다 — PR은 그대로 두고, PR 본문 ⚠️의 Issue가 머지된 뒤 `make ship`을 다시. "완료로 닫히지 않음"·"'#' 없는 번호"면 Issue의 머지 조건 줄을 사람이 고친다. "판정 실패"·"조회 실패"면 네트워크·`gh auth status`를 확인하고 `make ship`을 다시 |
| ship "테이블 SQL 초안이 있는 계약이 바뀜" | 루프 자동 머지(`TICKET_LOOP_MERGE=1`)의 G3 — 사람이 계약의 스키마를 보고 GitHub에서 머지한다 (PR은 그대로) |
| ship "마이그레이션이 계약의 테이블 SQL 초안과 다름" | 출력된 문장을 계약 초안(main)과 맞추거나, 계약부터 바꾸는 PR을 먼저. 의도한 차이면 사람이 확인하고 GitHub에서 머지 |
| ship "AI 리뷰 수정 필요" | PR 본문 "AI 리뷰"의 차단·높음 지적을 고치고 커밋 → `make ship`. 재리뷰에서는 "이전 지적 처리" 표의 미해결과 "이번 변경 ✓"인 높음만 막는다 |
| ship "머지 실패 — 보호 규칙" | 배정 레포에 승인 필수 규칙이 있으면 팀원이 `gh pr review <번호> --approve` 후 다시 `make ship` |
| `make sync` 충돌 | `/pr-check`. 남의 기능·공용 파일이면 담당자와 상의 |
