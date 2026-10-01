---
name: team-status
description: 팀 전체 현황 요약 — 멤버별 작업, 열린 PR, 충돌 위험. 팀 현황이나 누가 뭘 하는지 물을 때 사용.
---
다음을 읽는다: `docs/status/*.md`, `tasks/*.md`, `git fetch -q origin && git branch -r`, `git worktree list`, `git log --oneline -15 origin/main`, `gh pr list --state open`.

표로 요약한다:
- 멤버별 현재 작업 / 상태 / 막힌 것 (status 파일이 오래됐으면 표시)
- 열린 PR: 작성자, CI 상태, 리뷰 대기 여부
- 의존 관계상 대기 중인 작업
- 같은 파일을 건드리는 브랜치 쌍 (`git diff --name-only origin/main...<branch>` 교집합) → 충돌 위험
