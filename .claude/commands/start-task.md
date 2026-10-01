---
description: 새 작업 시작 (task 파일 + 브랜치/worktree 생성)
argument-hint: <member> <task-id> <설명>
---
새 작업을 시작한다. 인자: $ARGUMENTS

1. `docs/TEAM.md`로 멤버의 소유 영역을 확인한다.
2. `tasks/<task-id>-<설명>.md`가 없으면 `tasks/README.md` 템플릿으로 만든다 (상태: doing). 목표/완료 조건은 사용자에게 물어 채운다.
3. 현재 디렉터리가 main이고 미커밋 변경이 없으면 `git checkout -b <member>/<task-id>-<설명>`.
   이미 다른 작업 중이면 `scripts/new-worktree.sh <member> <task-id> <설명>`로 worktree를 만들고 경로를 안내한다.
4. `docs/status/<member>.md`의 현재 작업/브랜치/업데이트 시각을 갱신한다.
5. 작업이 `docs/CONTRACTS.md`의 계약에 의존하면 해당 부분을 요약해 보여준다. 계약이 없으면 계약부터 정하자고 제안한다.
