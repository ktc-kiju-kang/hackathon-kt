---
name: start-task
description: 이슈 작업 시작 — 본인 assign, 브랜치 또는 worktree 생성, 관련 계약 요약. 칸반 카드를 가져가 작업을 시작할 때 사용.
argument-hint: <이슈번호>
disable-model-invocation: true
---
이슈 작업을 시작한다: $ARGUMENTS

1. 이슈 번호가 없으면 `gh issue list --state open --search "no:assignee"`로 미배정 이슈를 보여주고 고르게 한다. 이슈 자체가 없으면 `/new-issue`를 제안한다.
2. `gh issue view <번호>`로 목표·완료 조건·의존 이슈를 읽고 요약한다. 의존 이슈가 아직 열려 있으면 알린다.
3. 다른 사람이 assign돼 있으면 멈추고 사용자에게 확인한다. 아니면 `gh issue edit <번호> --add-assignee @me`.
4. feature 이름(이슈 제목의 `[feature]`, 없으면 제안)과 짧은 설명으로 브랜치 `feat/<번호>-<설명>`(버그면 `fix/`)을 최신 main 기준으로 만든다:
   - 현재 main이고 미커밋 변경이 없으면: `git fetch origin main && git checkout -b <branch> origin/main`
   - 이미 다른 작업 중이면: `scripts/new-worktree.sh <번호> <설명> [type]` 후 경로 안내
5. 작업 범위를 안내한다: `frontend/src/app/<route>/`, `frontend/src/features/<feature>/`, `backend/app/{routers,services,schemas}/<feature>.py`, `backend/tests/test_<feature>.py`, `docs/contracts/<feature>.md`, (DB) `database/migrations/`.
   - 같은 기능 파일을 다른 열린 PR/브랜치가 건드리고 있으면(`gh pr list`, `git branch -r`) 충돌 위험을 알린다.
6. 이 기능이 쓰는 기존 계약(`docs/contracts/`)을 요약한다. 새 API가 필요하면 `/add-endpoint`로 계약부터 정하자고 제안한다.
7. 칸반 카드를 In Progress로 옮긴다:
   ```bash
   item=$(gh project item-add 1 --owner ktc-kiju-kang --url <이슈 URL> --format json --jq .id)   # 이미 있으면 같은 id 반환
   gh project item-edit --project-id PVT_kwHODZOImM4BlTN_ --id "$item" \
     --field-id PVTSSF_lAHODZOImM4BlTN_zhkAnc8 --single-select-option-id c73842c3
   ```
   (Status 옵션 id: Todo=5ed4277e, In Progress=c73842c3, In Review=180f967e, Done=d85b72df) `project` 권한 오류면 `gh auth refresh -h github.com -s project` 안내.
