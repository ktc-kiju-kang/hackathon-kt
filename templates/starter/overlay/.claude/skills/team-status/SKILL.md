---
name: team-status
description: 팀 전체 현황 요약 — REQ별 진행·검증 상태, 담당자별 Issue, 열린 PR·CI, 같은 파일을 건드리는 충돌 위험, 제출 문서 검사. 팀 현황이나 누가 뭘 하는지 물을 때 사용.
---
다음을 조회한다:
- `gh issue list --state all --limit 100 --json number,title,state,stateReason,assignees`
- `gh pr list --state open --json number,title,author,headRefName,statusCheckRollup`
- `git fetch -q origin && git log --oneline -10 origin/main`
- `docs/prd.md` 요구사항 표(REQ·Issue·상태), `python3 scripts/check-docs.py --draft`의 요약 줄

표로 요약한다:
- REQ별: Issue 번호·담당자·Issue 상태(open / completed / not planned)·prd 상태(계획~검증됨)·TC PASS 수
- 이상 신호: Issue가 닫혔는데 prd 상태가 `검증됨`이 아님, `검증됨`인데 TC가 PASS가 아님, Issue 없는 REQ, REQ 없는 Issue, completed가 아닌 사유로 닫힌 완료 작업
- 완료 진행률: completed Issue ÷ (전체 − not planned)
- 열린 PR: 작성자, 연결 Issue, CI 상태
- 충돌 위험: 열린 PR들의 변경 파일(`gh pr diff <n> --name-only`) 교집합, 공용 파일과 `database/migrations/` 번호 중복
- 마감(2026-10-15 00:00)까지 남은 시간과 미검증 REQ 목록
