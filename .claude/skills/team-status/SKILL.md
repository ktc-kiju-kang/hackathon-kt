---
name: team-status
description: 팀 전체 현황 요약 — 담당자별 이슈, 열린 PR·CI·리뷰 대기, 같은 파일을 건드리는 충돌 위험. 팀 현황이나 누가 뭘 하는지 물을 때 사용.
---
다음을 조회한다:
- `gh project item-list 1 --owner ktc-kiju-kang --format json --limit 100` (카드별 Status·assignee; `project` 권한 없으면 아래 이슈 목록으로 대체)
- `gh issue list --state open --limit 50 --json number,title,assignees,labels`
- `gh pr list --state open --json number,title,author,headRefName,reviewDecision,statusCheckRollup`
- `git fetch -q origin && git log --oneline -10 origin/main`

표로 요약한다:
- 칸반 컬럼별(Todo / In Progress / In Review / Done) 카드 수와 목록, 담당자별 진행 중 카드
- 이상 신호: assign됐는데 Todo에 있음, In Progress인데 assignee 없음, In Review인데 연결 PR 없음
- 열린 PR: 작성자, 연결 이슈, CI 상태, 리뷰 대기 여부 → 리뷰가 필요한 사람에게 알림
- 충돌 위험: 열린 PR들의 변경 파일(`gh pr diff <n> --name-only`) 교집합, 특히 공용 파일(`layout.tsx`, `src/app/page.tsx`, `api-client.ts`, `app/core/`, `package.json`, `requirements*.txt`)과 `database/migrations/` 번호 중복
- 의존 이슈가 열려 있어 막힌 작업
