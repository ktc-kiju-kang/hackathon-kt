---
name: new-issue
description: 작업 Issue 생성 — 요구사항 정의서(prd.md + docs/prd/REQ-xx)의 REQ 하나를 주최 측 양식에 맞춰 요구사항 근거·목적·완료 조건(AC)·연결 문서를 채워 Issue로 만든다. 역할 분담 방식이면 pm 에이전트의 티켓 초안(.run/tickets/)으로 [plan]·[BE]·[FE] Issue를 만든다. 새 기능이나 할 일을 Issue로 올리거나 기능을 쪼갤 때 사용.
argument-hint: <REQ-ID 또는 기능 설명>
---
Issue를 만든다: $ARGUMENTS

1. `docs/prd.md` 인덱스에서 해당 REQ를, 그 ID 칸이 링크한 하위 정의서(`docs/prd/REQ-01-….md`)에서 근거 원문(SRC)과 AC를 찾는다. **REQ가 없으면 먼저 인덱스 한 줄 + 하위 정의서를 추가하자고 제안**한다 (출처: 주최/팀 구분).
2. `.github/ISSUE_TEMPLATE/`의 주최 측 양식(`development-task.md`, 없으면 있는 양식)을 읽고 그 형식으로 본문을 쓴다:
   - 제목: 기본 방식은 `[REQ-01] <사용자 관점 요약>`. 역할 분담 방식(`docs/requirements-flow.md` 2절)은 `[REQ-01][plan|BE|FE] <요약>`
   - 요구사항 근거(정의서 경로 @ 커밋 SHA, REQ 문장, SRC 인용 — `docs/requirements-flow.md` 3절) / 목적 / 완료 조건 = AC 체크리스트 (`- [ ] AC-01-1 …`, 하위 정의서 문장 그대로) / 담당자 / 연결 문서(`docs/prd/REQ-01-….md`, 시험 TC-01-*) / 구현·검증 근거(작업 후 추가)
   - **역할 분담 방식**이면 본문을 새로 쓰지 않고 `pm` 에이전트가 만든 `.run/tickets/NN-….md` 초안(첫 줄 제목, 둘째 줄 `labels:`)을 쓴다. 사람이 `distribution.md`(분배표·AC 대조표)를 승인(G2)한 경우에만. 초안의 근거 SHA가 지금 정의서와 다르면(`git diff <SHA> -- docs/prd.md docs/prd/`) 멈추고 PM에게 다시 맡긴다.
3. 하루 안에 끝나지 않을 크기면 독립적으로 머지 가능한 REQ 여러 개로 쪼개자고 제안한다.
4. `gh issue list --state open`으로 중복·의존 관계를 확인한다.
5. 초안을 사용자에게 보여주고 확인받은 뒤 생성한다: `gh issue create --title "..." --body "..." --label ...` (담당자가 정해졌으면 `--assignee <id>`). 양식·초안에 라벨이 있으면 같이 붙인다. 역할 라벨(`plan`·`role:architect`·`role:backend`·`role:frontend`)이 레포에 없으면 같은 확인에서 `gh label create`로 먼저 만든다. 여러 개면 목록으로 한 번에 확인받고, 선행 관계(`선행: 04`)는 만든 번호(`#12`)로 바꿔 적는다 — `- 선행:` 줄에는 먼저 머지돼야 하는 Issue 번호만 둔다 (`/ticket-loop`가 그 Issue들이 닫힐 때까지 기다린다).
6. Issue 번호를 `docs/prd.md` 요구사항 표의 Issue 칸(역할 분담이면 플랜 티켓, 플랜이 없으면 첫 개발 티켓)에 적자고 안내하고, 바로 시작하려면 `/start-task <번호>`.
