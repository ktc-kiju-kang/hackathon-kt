---
name: start-task
description: Issue 작업 시작 — 본인 assign, 브랜치 또는 worktree 생성, 관련 REQ·AC·계약 요약, 시험 시나리오 먼저 적기. Issue를 가져가 작업을 시작할 때 사용.
argument-hint: <이슈번호>
disable-model-invocation: true
---
Issue 작업을 시작한다: $ARGUMENTS

1. Issue 번호가 없으면 먼저 내게 배정된 것(`gh issue list --state open --assignee @me`), 그다음 미배정(`--search "no:assignee"`)을 보여주고 고르게 한다. `make claims`에 이미 선점된 번호는 빼고 보여 준다. 없으면 `/new-issue`를 제안한다.
2. `gh issue view <번호>`로 목적·완료 조건을 읽고, 제목의 REQ ID로 `docs/prd.md`의 REQ·AC를 찾아 요약한다.
3. **선점**: `scripts/claim.sh take <번호>` — GitHub에 `claim/<번호>` 브랜치를 없을 때만 만들고(원자적) 본인을 assign한다. 실패("○○ 님이 이미 잡았습니다", "이미 ○○ 님에게 배정")하면 **여기서 멈추고** 사용자에게 알린다 — 직접 assign하거나 `--force`로 가져가지 않는다. 경고("○○ 님도 배정")가 나오면 그대로 전한다.
4. 브랜치 `feat/<번호>-<설명>`(버그면 `fix/`)을 최신 main 기준으로 만든다:
   - 현재 main이고 미커밋 변경이 없으면: `git fetch origin main && git checkout -b <branch> origin/main`
   - 이미 다른 작업 중이면: `scripts/new-worktree.sh <번호> <설명> [type]` 후 경로 안내
5. **시험부터**: 이 REQ의 TC가 `docs/e2e-test.md`에 없으면 AC마다 GIVEN/WHEN/THEN 시나리오를 상태 `미실행`으로 먼저 적는다 (정상·오류·권한 경계).
6. 작업 범위를 안내한다: `frontend/src/app/<route>/`, `frontend/src/features/<feature>/`, `backend/app/{routers,services,schemas}/<feature>.py`, `backend/tests/test_<feature>.py`, `docs/contracts/<feature>.md`, (DB) `database/migrations/`. 같은 파일을 다른 열린 PR이 건드리면(`gh pr list`) 알린다.
7. 새 API가 필요하면 `/add-endpoint`로 계약부터 정하자고 제안한다. 보안 기준(`docs/security-policy.md`) 중 이 REQ에 해당하는 SEC가 있으면 짚어 준다.
