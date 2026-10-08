# 제출 문서 템플릿 사용법

> 본선(10/14~15) 배정 레포에 넣을 **문서 8개의 뼈대**다. 이 파일(`GUIDE.md`)은 복사하지 않는다.
> 근거: AID-X 참가자 온보딩 사이트의 "문서 8개" 안내 (2026-10-08 확인). 세부 기준은 최종 공지를 따른다.

## 왜 이 문서들이 중요한가
- 기술평가 70점(18개 항목, 보안 10점 포함)은 Claude·Codex·Copilot 세 AI가 **문서·코드·실행/테스트 결과·GitHub 이력·AI 활용 기록**을 보고 매긴다.
- **분량이나 파일 수로는 점수가 오르지 않는다.** 문서는 평가자가 근거를 찾아가는 안내판이다.
- 그래서 모든 문서는 하나의 사슬로 이어져야 한다:
  **REQ(요구) → AC(확인 조건) → Issue·코드 → TC(시험) → 실제 결과(SHA·로그·화면)**
- 예시·계획·미검증을 "완료"로 쓰지 않는다. 확인 못 한 것은 `미검증`, 안 한 것은 `미실행`, 해당 없는 것은 `해당 없음 + 이유`.

## 파일
| 파일 | 내용 | 언제 쓰나 |
|---|---|---|
| `README.md` | 한 줄 소개, 실행 방법, 8개 문서·결과로 가는 링크 | 처음 뼈대 → 마지막에 결과 링크 |
| `docs/project-brief.md` | 문제·대상 사용자·목표·범위(주최 요구 vs 팀 추가) | 주제 공개 직후 (1시간 안) |
| `docs/prd.md` | REQ·AC 표 — **모든 ID의 원본** | 주제 공개 직후 |
| `docs/arch.md` | 구성도·기술 선택 이유·데이터·API·REQ별 코드 위치 | 구현 시작 전 → 구현하며 갱신 |
| `docs/experience.md` | 화면 흐름·화면별 REQ·KDS 적용·오류/빈 상태 | 화면 만들 때 |
| `docs/development.md` | 개발 과정·AI 활용 기록(AI가 한 것 vs 사람이 확인·고친 것)·결정 | 계속 (작업 끝날 때마다 한 줄) |
| `docs/security-compliance.md` | `security-policy.md`의 SEC별 적용 여부·코드 위치·검증 결과 | 정책 확인 즉시 → 시험 후 |
| `docs/e2e-test.md` | 재현 절차, TC별 GIVEN/WHEN/THEN·명령·실제 결과 | 시나리오는 구현 전, 결과는 시험 후 |
| `scripts/check-docs.py` | 빠진 문서·남은 `{{자리표시}}`·끊긴 ID 사슬 검사 | 커밋 전, 제출 직전 |

## 본선 당일 순서 (주제 공개 → 마감 10/15 00:00)
0. **배정 레포를 먼저 확인한다.** 주최 측이 이미 넣어 둔 파일(`docs/security-policy.md`, `.github/ISSUE_TEMPLATE/development-task.md`, 혹시 문서 양식)이 있으면 **그쪽 양식을 우선**하고 이 템플릿의 내용만 옮긴다. `security-policy.md`는 고치지 않는다.
1. `templates/submission/` 아래를 배정 레포 루트로 복사한다 (`GUIDE.md` 제외).
   ```sh
   rsync -a --exclude GUIDE.md templates/submission/ <배정레포>/
   ```
2. `project-brief.md` → `prd.md`: 주제 요구를 REQ로 옮기고(출처=주최), 팀 아이디어는 출처=팀으로 따로 적는다. REQ마다 AC를 1개 이상.
3. REQ마다 GitHub Issue를 주최 양식(개발 작업·검증)으로 만든다. Issue 제목에 `[REQ-01]`.
4. `e2e-test.md`에 TC 시나리오(GIVEN/WHEN/THEN)를 **구현 전에** 적는다. 상태는 `미실행`.
5. `security-compliance.md`에 SEC 행을 정책 그대로 만들고 적용/해당 없음을 먼저 정한다.
6. 구현하면서 `arch.md`의 "REQ별 코드 위치", `development.md`의 AI 활용 기록을 채운다.
7. 시험을 **직접 실행**하고 TC에 명령·SHA·PASS/FAIL·근거 경로를 채운다. Issue 본문에 커밋 주소·테스트 결과를 붙이고 **Close as completed**.
8. `python3 scripts/check-docs.py` 통과 → push → 40자 SHA로 포털 제출.

## ID 규칙
| ID | 뜻 | 정의하는 곳 | 참조하는 곳 |
|---|---|---|---|
| `REQ-01` | 요구사항 | `prd.md` | 모든 문서, Issue 제목 |
| `AC-01-1` | REQ-01의 1번 확인 조건 | `prd.md` | `e2e-test.md`, Issue 완료 조건 |
| `TC-01-1` | AC-01-1을 확인하는 1번 시험 | `e2e-test.md` | `security-compliance.md`, Issue 근거 |
| `TC-S01-1` | SEC-01을 확인하는 1번 시험 | `e2e-test.md` | `security-compliance.md` |
| `SEC-01` | 주최 보안 기준 항목 | `security-policy.md` (주최) | `security-compliance.md`, `e2e-test.md` |
| `ADR-01` | 기술 결정 | `arch.md` | `development.md` |

## 상태 값 (문서 전체 공통)
번호 자리수는 두 자리로 통일한다 (`REQ-01`). 검사 스크립트는 `REQ-1`도 같은 ID로 본다.
- REQ: `검증됨`(TC PASS) · `구현됨-미검증` · `진행 중` · `계획` · `제외(이유)`
- TC: `PASS` · `FAIL` · `SKIP(이유)` · `미실행`
- SEC: `적용-검증됨` · `적용-미검증` · `해당 없음(이유)` · `예외(이유·검토 상태)`

## Claude에게 맡길 때
- "prd.md의 REQ를 기준으로 e2e-test.md TC 시나리오 초안을 써줘. 상태는 미실행으로" 처럼 **ID를 기준으로** 시킨다.
- 결과 칸(실제 결과·PASS/FAIL)은 **명령을 실제로 실행한 출력으로만** 채운다. 실행하지 않았으면 `미실행`.
- AI가 틀린 것을 사람이 잡은 사례는 바로 `development.md` "AI 활용 기록"에 적는다 — 발표(AI 검증)와 평가 모두의 근거다.
