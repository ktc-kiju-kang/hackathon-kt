---
name: start-task
description: 새 작업 시작 — task 파일 생성, 브랜치 또는 worktree 생성, status 갱신. 사용자가 새 기능/작업을 시작하려 할 때 사용.
argument-hint: <member> <task-id> <설명>
disable-model-invocation: true
---
새 작업을 시작한다. 인자: $ARGUMENTS (member: a|b|c, task-id: T-xxx, 설명: kebab-case)

1. 인자가 부족하면 물어본다. task 번호는 멤버 대역(a=001~299, b=300~599, c=600~899)에서 `tasks/`에 없는 다음 번호를 제안한다.
2. `docs/TEAM.md`로 멤버의 소유 영역을 확인하고, 작업이 다른 영역을 건드릴 것 같으면 미리 알린다.
3. `tasks/<task-id>-<설명>.md`를 `tasks/README.md` 템플릿으로 만든다 (상태: doing). 목표·완료 조건은 사용자에게 물어 채운다.
4. 브랜치 `<member>/<task-id>-<설명>`을 최신 main 기준으로 만든다:
   - 현재 main이고 미커밋 변경이 없으면: `git fetch origin main && git checkout -b <branch> origin/main`
   - 이미 다른 작업 중이면: `scripts/new-worktree.sh <member> <task-id> <설명>` 후 경로를 안내한다.
5. `docs/status/<member>.md`의 업데이트 시각·현재 작업·브랜치를 갱신한다.
6. 작업이 API를 쓰거나 만들면 `docs/CONTRACTS.md`에서 관련 계약을 요약해 보여준다. 계약이 없으면 `/add-endpoint`로 계약부터 정하자고 제안한다.
