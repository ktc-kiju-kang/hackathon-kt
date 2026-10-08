---
name: handoff
description: 작업 마무리 — 검증, 시험 결과·근거 기록, reviewer 셀프리뷰, sync, `Closes #이슈` PR 생성, Issue에 근거 첨부. 작업이 끝났거나 PR을 올리려 할 때 사용.
disable-model-invocation: true
---
1. 브랜치명에서 Issue 번호를 확인하고(`feat/<번호>-...`) `gh issue view <번호>`의 완료 조건(AC)과 대조한다. 못 채운 AC가 있으면 알린다.
2. `git diff --stat origin/main...HEAD`로 변경 범위를 확인한다. 다른 기능의 파일·공용 파일·`database/migrations/` 추가가 있으면 표시한다.
3. 변경한 쪽의 검증을 **실제로 실행**하고 모두 통과시킨다:
   - `frontend/`: `cd frontend && npm run lint && npm test && npm run build`
   - `backend/`: `cd backend && .venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/ty check app tests && .venv/bin/pytest`
4. **근거 기록** (채점 근거):
   - `docs/e2e-test.md`: 이 REQ의 TC마다 실행 명령·실제 결과·상태(PASS/FAIL/SKIP(이유))·근거 경로를 **방금 실행한 출력으로** 채운다. 실행 안 한 것은 `미실행`.
   - `docs/prd.md`: TC가 모두 PASS면 REQ 상태를 `검증됨`, 아니면 `구현됨-미검증`.
   - `docs/arch.md` "REQ별 코드 위치", 보안 해당 시 `docs/security-compliance.md`.
   - AI가 틀려서 고친 일이 있었으면 `docs/development.md` "AI 활용 기록"에 한 줄.
   - `python3 scripts/check-docs.py --draft`로 끊긴 ID가 없는지 확인.
5. `reviewer` 서브에이전트로 셀프 리뷰하고 지적사항을 처리한다.
6. 커밋 후 `/pr-check`(충돌 검사) → `scripts/sync.sh`로 main 반영 → 검증 재실행 → `scripts/check-conflicts.sh` ❌ 0개.
7. `.github/pull_request_template.md` 형식으로 PR 본문 초안을 보여준다. 첫 줄 `Closes #<번호>`, REQ·TC ID와 시험 결과 요약을 넣는다.
8. 사용자 확인 후 `git push -u origin <branch>` → `gh pr create`. Claude는 머지하지 않는다.
9. 머지 후 Issue가 **completed**로 닫혔는지 확인하고, Issue 본문(또는 댓글)에 **커밋 주소와 테스트 명령·결과**를 붙이자고 안내한다 (`gh issue comment <번호> --body ...`, 사용자 확인 후).
