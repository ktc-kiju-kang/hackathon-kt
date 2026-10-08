# 파이프라인 — 기획부터 로컬 배포·제출까지

> 단계마다 **산출물**과 **통과 기준(게이트)** 이 있다. 게이트를 통과하지 못하면 다음 단계로 가지 않는다.
> 입구는 `make` 하나다 (`make help`). 모든 명령은 로컬에서 돌고, CI가 있으면 같은 검사를 한 번 더 한다.

## 한눈에
```
기획 ─▶ 설계 ─▶ 개발(Issue마다 반복) ─▶ 통합·로컬 배포 ─▶ 시험 기록 ─▶ 제출
/plan-topic  /add-endpoint  /start-task → 구현·시험 → /handoff   make serve   make e2e   make submit-check
```

| 단계 | 산출물 | 명령·스킬 | 게이트 (통과 기준) |
|---|---|---|---|
| 0. 준비 | 키트가 깔린 배정 레포, 의존성 | `export.py`(이 레포 밖에서) → `make setup` | `make verify` 전부 PASS |
| 1. 기획 | `project-brief.md`, `prd.md`(REQ·AC), TC 시나리오, SEC 매핑, Issue 분할안 | `/plan-topic` | `make docs` 오류 0 · 모든 REQ에 AC, 모든 AC에 TC · **팀 합의** |
| 2. 설계 | `docs/contracts/<feature>.md`, `arch.md`(구성·데이터·API), 마이그레이션 초안 | `/add-endpoint` 1단계(계약), ADR(`docs/decisions/`) | 화면·API 담당이 계약에 동의 |
| 3. 개발 | 브랜치·코드·테스트(이름에 TC ID), 문서 갱신 | `/new-issue` → `/start-task` → `/add-endpoint`·`/add-page` → `/handoff` | PR마다 `make verify` PASS · reviewer 지적 처리 · `Closes #` |
| 4. 통합·로컬 배포 | main 최신 코드가 프로덕션 빌드로 떠 있음 | `make serve` / `make status` / `make stop` | 스모크 PASS (health ok·db ok·**버전 = HEAD**·주요 화면 200) |
| 5. 시험 기록 | `e2e-test.md` 상태·근거, `prd.md` REQ 상태, `docs/evidence/<실행>/` | **main에서** `make e2e` → 결과만 담은 PR(`docs/evidence-<시각>`) 머지 | 전체 PASS, 커밋된 코드로 실행(`-dirty` 아님). PR에서는 `make e2e`로 확인만 하고 기록은 넣지 않는다 (충돌 방지) |
| 6. 제출 | 포털에 40자 SHA, 발표자료 | `make submit-check` → `/submit` | 깨끗한 트리 · origin/main = HEAD · `verify --strict` · 근거 이후 코드 변경 없음 |

## 각 명령이 하는 일
| 명령 | 내용 |
|---|---|
| `make setup` | Node 20+·Python 3.11+ 확인 → backend `.venv` + 의존성 → `npm ci` → `.env` 없으면 생성 (여러 번 실행해도 됨) |
| `make dev` | 개발 서버 (핫 리로드) api :8000 + web :3000, Ctrl+C로 둘 다 종료 |
| `make verify` | ruff·ty·pytest·e2e lint·eslint·vitest·next build(격리 폴더)·문서 검사·(있으면) gitleaks 커밋 이력. 하나가 실패해도 끝까지 돌고 요약, 로그 `.run/verify/`. `make serve` 중에 돌려도 된다 |
| `make serve` | **로컬 배포**: 프로덕션 빌드 → backend `fastapi run` + frontend `next start` 백그라운드(이 PC에서만, 127.0.0.1) → health·화면 스모크. 실패하면 스스로 내린다. 로그 `.run/` |
| `make e2e` | ① backend pytest·frontend vitest ② **격리 로컬 배포**(포트 18000/13000·새 DB·mock LLM)에 `e2e/` 시험 ③ TC별 결과를 `e2e-test.md`·`prd.md`에 기록, 근거(JUnit XML·로그·요약)를 `docs/evidence/`에 저장. `make serve`로 떠 있는 서버와 DB·빌드를 건드리지 않는다 |
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
| 공개 직후 ~1h | 키트 내보내기·`make setup`·`make verify` (1명) / 주제 분석·`/plan-topic` (2명) | 기획 게이트 |
| ~2h | 계약·arch 초안, REQ별 Issue 생성·배정 (REQ 하나 = Issue 하나 = 한 사람) | 설계 게이트 |
| ~20:00 | 개발 반복: Issue마다 `/start-task` → 시험부터 → 구현 → `/handoff` → 머지. **2~3시간마다 main에서 `make e2e`** | PR마다 verify |
| 20:00 | **기능 동결.** 새 REQ 금지, 미완성 REQ는 `제외(이유)` 또는 `구현됨-미검증`으로 정직하게 | — |
| 20:00~22:00 | 버그 수정, 문서 8개 채우기, 보안 준수표, AI 활용 기록 정리 | `make docs` 오류 0 |
| 22:00 | main에서 `make e2e` → 결과 커밋·push | 전부 PASS |
| 22:30 | `make submit-check` → 포털에 SHA 제출, 발표자료 업로드 | 제출 게이트 |
| ~23:30 | 여유 (재제출이 필요하면 고친 뒤 `make e2e` → `make submit-check` 다시) | — |

## 문제가 생기면
| 증상 | 할 일 |
|---|---|
| `make serve` "포트 사용 중" | `make stop`. 다른 프로그램이면 `API_PORT=8100 WEB_PORT=3100 make serve` |
| 스모크 `version != HEAD` | 서버가 예전 코드. `make stop && make serve` |
| `make e2e` 배포 실패 | `.run/e2e/serve.log`, `.run/e2e-serve/*.log` |
| 머지 후 main이 깨짐 | 고치는 데 10분 이상이면 `git revert <머지 커밋>` → PR → 머지. 제출 마감 직전에는 되돌리기가 기본 |
| LLM 한도·장애 | mock으로도 화면·흐름이 동작한다. 발표에서는 녹화·캡처로 |
| DB가 꼬임 (로컬) | `make stop && rm backend/data/app.db && make serve` (마이그레이션이 처음부터 다시 적용) |
| CI가 안 돎 (사내 GHE) | `make verify` 결과를 PR 본문에 붙인다 (`/handoff`가 한다) |
