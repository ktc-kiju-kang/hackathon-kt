---
name: handoff
description: 작업 마무리 — 완료 조건 대조, 테스트 이름의 TC ID 확인, 문서 갱신 후 make ship(검사·시험·PR·AI 리뷰·자동 머지)을 실행하고 결과를 처리한다. 작업이 끝났거나 PR을 올리려 할 때 사용.
disable-model-invocation: true
---
작업을 main까지 보낸다 (파이프라인 3단계 끝, `docs/pipeline.md`).

1. **완료 조건 대조** — 브랜치명의 Issue 번호(`feat/<번호>-...`)로 `gh issue view <번호>`의 AC와 구현을 대조한다. 못 채운 AC가 있으면 사용자에게 알리고, 이번 PR에서 뺄지(Issue를 나눌지) 묻는다.
2. **시험 연결** — 다른 사람의 기능에 의존하는 E2E(예: 남이 만드는 등록 API를 불러야 하는 목록 시험)는 **그 기능이 main에 머지된 뒤**에 넣는다. 그 전에는 backend 테스트에서 DB에 직접 넣어 시험한다 — 아니면 ship이 e2e에서 멈춘다. 이 REQ의 AC마다 테스트가 있고 **이름에 TC ID**가 들어갔는지 확인한다 (`backend/tests/test_<feature>.py`의 `test_tc_01_3_...`, 사용자 흐름은 `e2e/test_<feature>.py`). `docs/e2e-test.md` 시험 목록에 그 TC 행이 있는지도. 수동 시험 TC만 명령·결과를 직접 적는다.
3. **문서** — `docs/arch.md` "REQ별 코드 위치", 계약(`docs/contracts/`), 보안 해당 시 `docs/security-compliance.md`, AI가 틀려 고친 일이 있었으면 `docs/development.md` "AI 활용 기록"에 한 줄. **`docs/e2e-test.md` 상태·`docs/prd.md` 상태·`docs/evidence/`는 고치지 않는다** (`make record`만 쓴다).
4. 커밋 (`<type>(<feature>): <요약> (REQ-01)`) → **`make ship`** 실행. 순서: main 반영 → `make verify` → 충돌 검사 → `make e2e`(확인만) → push·PR(`Closes #`) → AI 리뷰(PR 본문 블록, `reviewer` 헤드리스) → Issue 근거 댓글 → 머지 잠금 → CI → squash 머지 → main 확인.
5. **멈췄을 때** — 단계별로 원인을 읽고 고친 뒤 커밋하고 `make ship`을 다시 한다.
   - verify·e2e 실패: `.run/ship-*.log`. 테스트를 지우거나 skip으로 숨기지 않는다.
   - 충돌 검사 ❌ / sync 충돌: `/pr-check`. 남의 기능·공용 파일이면 사용자와 담당자에게 확인.
   - AI 리뷰 "수정 필요"(차단·높음·점수 미달): PR 본문 "AI 리뷰"의 지적을 고친다. 지적이 틀렸다고 판단되면 사용자에게 근거와 함께 보여 주고, 사용자가 정하면 `SHIP_NO_MERGE=1 make ship`으로 PR만 두고 팀원이 확인 후 `gh pr merge --squash`.
   - 머지 잠금 대기: 다른 사람이 머지 중 (`make lock-status`). 기다리면 된다.
   - 머지 후 main 검사 실패: 출력된 되돌리기 명령으로 revert 브랜치를 만들어 `make ship`.
6. 머지되면 Issue가 completed로 닫혔는지, 근거 댓글이 달렸는지 확인한다 (ship 마지막 줄). 다음 작업은 `/start-task`.
