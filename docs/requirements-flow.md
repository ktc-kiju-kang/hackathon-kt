# 요구사항 → 정의서 → 티켓 — PO·PM·역할 에이전트

> 사람이 요구사항을 주면 **PO 에이전트**가 분석해 요구사항 정의서(`docs/prd.md` 인덱스 + REQ별 `docs/prd/REQ-xx-….md`)를 만들고, **PM 에이전트**가 그 정의서로 플랜·개발 티켓을 만들어 **아키텍트·백엔드·프론트** 에이전트에게 나눈다.
> 모든 티켓에는 정의서의 어느 요구에서 나왔는지 **근거**가 들어간다. 근거가 없는 티켓은 만들지 않는다.
> 파이프라인 전체에서의 위치: `docs/pipeline.md` 1단계(기획)·2단계(설계)·3단계(개발)의 입구.

## 한눈에
```
사람: 요구사항 원문
   │
   ▼
PO ── 분석·질문 ──▶ docs/prd.md (인덱스: 원문 SRC·REQ 표·상태)  ◀ G1 사람이 정의서 승인
   │                 └ docs/prd/REQ-01-….md (REQ별 근거·AC)
   │                 SRC(원문) → REQ → AC → TC
   ▼
PM ── 분해·배분 ──▶ 티켓 분배표 (REQ마다 플랜 1 + 개발 N)    ◀ G2 사람이 분배표 승인 → Issue 생성
   │
   ├─▶ 아키텍트: 플랜 티켓  [REQ-01][plan]  계약·arch·마이그레이션   ◀ G3 계약 PR 머지
   ├─▶ 백엔드:   개발 티켓  [REQ-01][BE]    API·서비스·테스트·E2E
   └─▶ 프론트:   개발 티켓  [REQ-01][FE]    화면·api.ts·화면 확인
                    │
                    ▼
               make ship (티켓마다)                          ◀ G4 검사·시험·AI 리뷰·머지
```

## 역할

| 역할 | 입력 | 하는 일 | 산출물 | 하지 않는 것 |
|---|---|---|---|---|
| **PO** | 요구사항 원문, `docs/security-policy.md`, 마감 | 원문을 문장 단위로 나눠 SRC ID를 붙이고, REQ·AC·TC로 바꾼다. 애매한 것은 추측하지 않고 질문으로 남긴다. 범위 안/밖·우선순위를 정한다 | `docs/prd.md`(인덱스), `docs/prd/REQ-xx-….md`(REQ별), `docs/e2e-test.md` 시험 목록(상태 `미실행`), 질문 목록 | 티켓 생성, 담당 배정, 구현 방법 결정 |
| **PM** | 승인된 `docs/prd.md`(커밋 SHA) | REQ마다 플랜·개발 티켓으로 쪼개고 역할에 배분한다. 머지 순서·의존을 정한다. AC가 빠짐·중복 없이 티켓에 하나씩 배정됐는지 확인한다 | 티켓 분배표, GitHub Issue | REQ·AC 추가·수정(→ PO에게 요청), 코드 작성 |
| **아키텍트** | 플랜 티켓 | API 계약, 화면·API·테이블 구성, 마이그레이션 초안, 필요하면 ADR | `docs/contracts/<feature>.md`, `docs/arch.md` REQ 블록, `docs/decisions/` | 기능 구현 |
| **백엔드** | 개발 티켓 `[BE]` + 머지된 계약 | `/start-task` → `/add-endpoint`(2단계부터) → `make ship` | `backend/app/{routers,services,schemas}/<feature>.py`, `tests/test_<feature>.py`, `e2e/test_<feature>.py`, 마이그레이션 | 계약 변경(→ 아키텍트), 화면 |
| **프론트** | 개발 티켓 `[FE]` + 머지된 계약 | `/start-task` → `/add-page` → `make ship` | `frontend/src/app/<route>/`, `frontend/src/features/<feature>/`, 메뉴 한 줄 | 계약 변경(→ 아키텍트), API |
| (리뷰어) | PR | 이미 있는 `reviewer` 에이전트가 `make ship` 안에서 리뷰한다 | PR 본문 "AI 리뷰" | 코드 수정 |

역할끼리 일을 넘길 때는 **Issue 댓글**로 한다 (근거가 GitHub에 남는다). 예: 백엔드가 계약에 없는 필드가 필요하면 플랜 티켓에 댓글 → 아키텍트가 계약 PR.

## 1. PO — 요구사항 정의서

요구사항 정의서는 **부모 인덱스 `docs/prd.md` + REQ마다 하위 정의서 `docs/prd/REQ-<번호>-<영문 설명>.md`** 다. `prd.md`는 제출 문서 8개 중 하나라 이름을 바꾸지 않고, 상세를 하위 파일로 나눈다. 양식은 `templates/submission/docs/prd.md`와 `docs/prd/REQ-01.md`.

```
docs/prd.md                        인덱스 — 원문(SRC) · 요구사항 표(상태) · 비기능 · 가정·질문 · 범위 밖
docs/prd/REQ-01-todo-create.md     REQ-01 — 근거 원문 인용 · 설명 · 확인 조건(AC) 표 · 가정 · 변경 이력
docs/prd/REQ-02-todo-list.md       REQ-02 — …
```

| 어디 | 절 | 규칙 |
|---|---|---|
| 인덱스 | 원문 (SRC) | 받은 요구사항을 **고치지 않고** 문장·항목 단위로 나눠 `SRC-01`부터 번호. 모든 SRC는 REQ의 출처나 "범위 밖"으로 한 번 이상 이어진다 |
| 인덱스 | 요구사항 표 | `\| ID \| 출처 \| 요구사항 \| 우선순위 \| Issue \| 확인 조건 \| 상태 \|`. ID 칸은 하위 정의서 링크 `[REQ-01](prd/REQ-01-todo-create.md)`, 출처는 `주최 (SRC-02, SRC-03)`·`팀`, 확인 조건은 그 하위 정의서의 AC 목록 그대로 (채점자가 인덱스만 읽어도 범위가 보인다). **상태는 이 표에만** (`make e2e`·`make record`가 갱신). Issue 칸은 PM이 플랜 티켓 번호를 적는다 |
| 인덱스 | 비기능 · 가정·미결 질문 · 범위 밖 | SEC는 `security-compliance.md`에서 그대로. 질문은 사람에게 묻고, 답을 받으면 REQ·AC에 반영, 못 받은 채 진행하면 **가정**으로 |
| 하위 | 근거 원문 · 관련 흐름 | 이 REQ가 나온 SRC를 인용 (팀 추가 REQ는 project-brief의 목표). 관련 흐름은 `experience.md`의 `FLOW-01` |
| 하위 | 확인 조건 (AC) | 정상·오류·(사용자별 데이터면) 권한 경계. 관찰 가능한 결과로. AC마다 TC ID. **AC 번호는 파일의 REQ 번호와 같아야** 한다 |
| 하위 | 변경 이력 | 날짜·변경·이유·Issue·TC (4절). REQ별 git 이력이 그대로 이 파일의 이력이다 |

`scripts/check-docs.py`(`make docs`)가 지키는 것: 링크한 하위 파일이 있는가, 링크되지 않은 `docs/prd/*.md`가 없는가(`_`로 시작하는 파일 제외), 링크가 자기 REQ 파일을 가리키는가, 하위 파일에 REQ 표가 없는가, AC 번호가 파일의 REQ와 맞는가, 인덱스의 '확인 조건' 칸이 실제 AC와 같은가, 이어지지 않은 SRC가 없는가, `experience.md`에 없는 FLOW를 가리키지 않는가(경고).

REQ 크기: **반나절 안에** 계약 + 백엔드 + 프론트 + 시험이 끝나는 크기. 크면 PO가 쪼갠다.

**G1 게이트 (사람):** `make docs`(= `check-docs.py --draft`) 오류 0, 질문 목록에 답했거나 가정으로 바꿈 → 사람이 정의서를 승인한다. PO는 승인된 정의서를 커밋하고 그 **커밋 SHA**를 PM에게 넘긴다. 이후 티켓의 근거는 이 SHA의 정의서다.

## 2. PM — 티켓 분배

PM은 승인된 정의서만 읽고 분배표를 만든다. 분배표는 사람에게 보여 줄 표이고, 승인되면 그대로 Issue가 된다.

| 티켓 | 제목 | 라벨 | 담당 역할 | 언제 시작 | 끝 |
|---|---|---|---|---|---|
| 플랜 | `[REQ-01][plan] <요약>` | `plan`, `role:architect` | 아키텍트 | 바로 | 계약·arch PR 머지 |
| 개발 BE | `[REQ-01][BE] <요약>` | `feature`, `role:backend` | 백엔드 | 플랜 머지 후 | `make ship` 머지 |
| 개발 FE | `[REQ-01][FE] <요약>` | `feature`, `role:frontend` | 프론트 | 플랜 머지 후 (계약의 mock으로 화면 먼저) | BE 머지 후 `make ship` 머지 |

분배 규칙:
- **AC 하나는 개발 티켓 하나가 책임진다.** API로 확인하는 AC(오류 응답·권한)는 BE, 화면으로 확인하는 AC(안내 문구·표시)는 FE. PM은 분배표 끝에 "AC → 티켓" 대조표를 붙여 빠짐·중복이 0인지 보인다.
- **같은 파일을 두 티켓이 고치지 않는다.** BE와 FE는 같은 기능 이름(`<feature>`)의 다른 폴더를 쓴다. 공용 파일이 필요하면 따로 `chore/shared-…` 티켓.
- **머지 순서:** REQ끼리는 PO가 정한 순서, REQ 안에서는 plan → BE → FE. E2E는 자기 REQ와 앞선 REQ의 API만 쓴다 (순환 금지, `CLAUDE.md` 충돌 방지 규칙).
- 개발 티켓 하나도 반나절 안에 끝나야 한다. 넘으면 REQ를 쪼개 달라고 PO에게 요청한다.
- prd.md 요구사항 표의 Issue 칸에는 **플랜 티켓 번호**를 적고, 플랜 티켓 본문에 그 REQ의 개발 티켓 목록을 체크리스트로 둔다.

**G2 게이트 (사람):** 분배표 + AC 대조표를 사람이 승인한 뒤에 Issue를 만든다 (`/new-issue`, 여러 개면 목록으로 한 번에 확인). 담당자 배정·선점은 실제로 작업을 시작할 때 `scripts/claim.sh`로 한다.

## 3. 티켓 양식 — 요구사항 근거

모든 티켓(플랜·개발)은 주최 측 양식(`.github/ISSUE_TEMPLATE/feature.yml`)의 목적·완료 조건·연결 문서 위에 **"요구사항 근거"** 절을 둔다.

```markdown
### 요구사항 근거
- 정의서: docs/prd/REQ-01-todo-create.md @ a1b2c3d (G1에서 승인된 판, 인덱스 docs/prd.md)
- REQ: REQ-01 — 사용자는 할 일을 등록할 수 있다
- 원문: SRC-02 "사용자는 할 일을 제목과 마감일로 등록한다"
- 이 티켓이 책임지는 AC: AC-01-1(오류), AC-01-3(권한)
- 시험: TC-01-1, TC-01-3 (docs/e2e-test.md)
- 분배 이유(PM): API 응답으로 확인하는 AC라 BE. 화면 AC-01-2는 #12(FE)
- 선행: #10 [REQ-01][plan] 머지 후 시작

### 목적
### 완료 조건 (AC)
- [ ] AC-01-1 필수 입력이 비면 422와 안내 문구
- [ ] AC-01-3 다른 사용자의 할 일은 조회되지 않는다
### 연결 문서
### 구현·검증 근거 (작업 후, make ship이 댓글로 남김)
```

플랜 티켓은 "책임지는 AC" 대신 **"이 계약이 받쳐야 하는 AC"**(그 REQ의 AC 전부)를 적는다.

근거 규칙:
- REQ·AC 문장은 하위 정의서에서 **그대로 복사**한다. 티켓에서 바꿔 쓰지 않는다.
- 근거에 없는 일을 하게 되면 티켓 범위를 넓히지 않는다. 티켓에 댓글로 PO에게 요청하고 PO가 정의서를 고친다.
- PR 본문·커밋 메시지에는 티켓 번호와 REQ ID를 적는다 (`feat(todo): 할 일 등록 API (REQ-01)`). 이 연결이 채점의 근거 사슬이다: **원문(SRC) → REQ → AC → 티켓 → 커밋·PR → TC → 시험 근거**.

## 4. 요구사항이 바뀔 때

**이유·Issue·시험을 함께** 고친다. 한쪽만 바뀌면 근거 사슬이 끊긴다.

1. PO가 그 REQ의 하위 정의서(AC·관련 흐름)와 필요하면 인덱스(요구사항 문장·'확인 조건' 칸)를 고친다. 하위 정의서 변경 이력에 `| 날짜 | 변경 | 이유 | Issue | TC |` 한 줄.
2. **같은 PR에서** 바뀐 AC의 TC 시나리오(`docs/e2e-test.md`의 GIVEN/WHEN/THEN·확인 조건 칸)와 테스트 코드를 고친다. 지운 AC의 TC는 지우고, 새 AC에는 TC를 만든다 (`make docs`가 AC↔TC 끊김을 잡는다). 흐름이 바뀌면 `experience.md`의 FLOW도.
3. PM이 영향을 받는 티켓마다 댓글: 바뀐 AC, 이유, 새 정의서 SHA. 완료 조건이 바뀌면 티켓 본문의 AC 체크리스트도 고친다.
4. 이미 머지된 개발 티켓의 AC가 바뀌면 **새 티켓**을 만든다 (닫힌 티켓을 다시 열지 않는다). 변경 이력의 Issue 칸에 새 번호.
5. 팀이 AI 안을 바꾼 결정은 `docs/development.md` "결정과 변경"에도 남긴다.

## 5. 지금 있는 것과 앞으로 만들 것

| 역할 | 지금 쓰는 장치 | 앞으로 |
|---|---|---|
| PO | `/plan-topic` 1~6단계 (정의서·TC·SEC 매핑) | `.claude/agents/po.md` — 원문 SRC 분해, 질문 목록, G1 전 자체 점검 |
| PM | `/plan-topic` 7단계, `/new-issue` | `.claude/agents/pm.md` — 분배표·AC 대조표, 역할 라벨로 Issue 생성 |
| 아키텍트 | `/add-endpoint` 1단계(계약), ADR | `.claude/agents/architect.md` |
| 백엔드·프론트 | `/start-task` → `/add-endpoint`·`/add-page` → `/handoff`. 자동으로 돌리면 `/ticket-loop` | `/ticket-loop`가 `role:` 라벨로 자기 역할의 티켓만 집게 한다 |
| 리뷰어 | `reviewer` 에이전트 (`make ship`) | 리뷰 항목에 "요구사항 근거와 변경 내용이 맞는가" 추가 |

**현재 상태:** 이 문서의 하위 정의서 분리(1절)와 요구사항 근거(3절)는 지금 적용된다 (양식·`check-docs.py`). 역할 에이전트·`role:` 라벨·역할별 티켓 분배(2절)는 위 "앞으로"를 만든 뒤에 적용하고, 그 전까지는 기존 "REQ 하나 = Issue 하나 = 한 사람"이 기본이다.

이 흐름은 기존의 "REQ 하나 = 한 사람이 frontend+backend+시험" 규칙(`feature.yml`, `/plan-topic` 7단계)을 **REQ 하나 = 플랜 1 + BE 1 + FE 1 티켓**으로 바꾼다. 위 "앞으로"를 만들 때 그 양식과 스킬도 함께 고친다.
