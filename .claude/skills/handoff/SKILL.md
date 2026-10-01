---
name: handoff
description: 작업 마무리 — 검증, reviewer 셀프리뷰, sync, `Closes #이슈` PR 생성. 작업이 끝났거나 PR을 올리려 할 때 사용.
disable-model-invocation: true
---
1. 브랜치명에서 이슈 번호를 확인하고(`feat/<번호>-...`) `gh issue view <번호>`의 완료 조건과 대조한다. 못 채운 항목이 있으면 알린다.
2. `git diff --stat origin/main...HEAD`로 변경 범위를 확인한다. 다른 기능의 파일이나 공용 파일 변경, `database/migrations/` 추가가 있으면 표시한다. 마이그레이션이 있으면 공유 DB 적용 여부를 사용자에게 확인한다.
3. 변경한 쪽의 검증을 실행하고 모두 통과시킨다:
   - `frontend/` 변경: `cd frontend && npm run lint && npm run build`
   - `backend/` 변경: `cd backend && .venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/pytest`
4. `reviewer` 서브에이전트로 셀프 리뷰하고 지적사항을 처리한다.
5. 커밋 후 `scripts/sync.sh`로 main 반영하고, 검증을 다시 돌린다.
6. `.github/pull_request_template.md` 형식으로 PR 본문 초안을 보여준다. 첫 줄 `Closes #<번호>`. 계약 변경·남의 기능/공용 파일 변경이 있으면 관련 담당자(이슈 assignee)를 리뷰어로 제안한다.
7. 사용자 확인 후 `git push -u origin <branch>` → `gh pr create` (리뷰어는 `--reviewer`). 머지는 사람이 한다.
8. 칸반은 자동으로 움직인다: PR 연결 → In Review, 머지 → Done. PR 본문에 `Closes #<번호>`가 없으면 연결되지 않으니 꼭 확인한다.
