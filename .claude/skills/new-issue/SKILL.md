---
name: new-issue
description: 작업 Issue 생성 — prd.md의 REQ 하나를 주최 측 양식(개발 작업·검증)에 맞춰 목적·완료 조건(AC)·연결 문서를 채워 Issue로 만든다. 새 기능이나 할 일을 Issue로 올리거나 기능을 쪼갤 때 사용.
argument-hint: <REQ-ID 또는 기능 설명>
---
Issue를 만든다: $ARGUMENTS

1. `docs/prd.md`에서 해당 REQ와 AC를 찾는다. **REQ가 없으면 먼저 prd.md에 REQ·AC를 추가하자고 제안**한다 (출처: 주최/팀 구분).
2. `.github/ISSUE_TEMPLATE/`의 주최 측 양식(`development-task.md`, 없으면 있는 양식)을 읽고 그 형식으로 본문을 쓴다:
   - 제목: `[REQ-01] <사용자 관점 요약>`
   - 목적 / 완료 조건 = AC 체크리스트 (`- [ ] AC-01-1 …`) / 담당자 / 연결 문서(`docs/prd.md`의 REQ-01, 시험 TC-01-*) / 구현·검증 근거(작업 후 추가)
3. 하루 안에 끝나지 않을 크기면 독립적으로 머지 가능한 REQ 여러 개로 쪼개자고 제안한다.
4. `gh issue list --state open`으로 중복·의존 관계를 확인한다.
5. 초안을 사용자에게 보여주고 확인받은 뒤 생성한다: `gh issue create --title "..." --body "..."` (담당자가 정해졌으면 `--assignee <id>`). 양식에 라벨이 있으면 같이 붙인다.
6. Issue 번호를 `docs/prd.md` 요구사항 표의 Issue 칸에 적자고 안내하고, 바로 시작하려면 `/start-task <번호>`.
