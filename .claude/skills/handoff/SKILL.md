---
name: handoff
description: 작업 마무리 — 검증, reviewer 셀프리뷰, task/status 갱신, sync, PR 생성. 작업이 끝났거나 PR을 올리려 할 때 사용.
disable-model-invocation: true
---
1. `git diff --stat origin/main...HEAD`로 변경 범위를 확인한다.
2. 변경한 쪽의 검증을 실행하고 모두 통과시킨다 (CLAUDE.md "명령" 표):
   - `web/` 변경: `cd web && npm run lint && npm run build`
   - `api/` 변경: `cd api && .venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/pytest`
3. `reviewer` 서브에이전트로 셀프 리뷰하고 지적사항을 처리한다.
4. 해당 `tasks/T-xxx-*.md` 상태를 review로 바꾸고 완료 조건을 체크한다.
5. `docs/status/<member>.md` 갱신 (업데이트 시각, 다음 할 일, 막힌 것).
6. 커밋 후 `scripts/sync.sh`로 main 반영.
7. `.github/pull_request_template.md` 형식으로 PR 본문 초안을 보여준다. 계약 변경이나 다른 소유 영역 변경이 있으면 해당 owner를 리뷰어로 제안한다.
8. 사용자 확인 후 `git push -u origin <branch>` → `gh pr create`. 머지는 사람이 한다.
