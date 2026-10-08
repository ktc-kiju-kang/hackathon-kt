---
name: handoff
description: 작업 마무리 — 검증, 시험 결과·근거 기록, reviewer 셀프리뷰, sync, `Closes #이슈` PR 생성, Issue에 근거 첨부. 작업이 끝났거나 PR을 올리려 할 때 사용.
disable-model-invocation: true
---
1. 브랜치명에서 Issue 번호를 확인하고(`feat/<번호>-...`) `gh issue view <번호>`의 완료 조건(AC)과 대조한다. 못 채운 AC가 있으면 알린다.
2. `git diff --stat origin/main...HEAD`로 변경 범위를 확인한다. 다른 기능의 파일·공용 파일·`database/migrations/` 추가가 있으면 표시한다.
3. `make verify`를 **실제로 실행**하고 모두 PASS시킨다 (CI와 같은 검사). 사내 CI가 안 돌면 마지막 요약 줄을 PR 본문에 붙인다.
4. **근거 기록** (채점 근거):
   - 이 REQ의 테스트 이름에 TC ID가 들어갔는지 확인한다 (`test_tc_01_3_...`, e2e는 `e2e/test_<feature>.py`).
   - `make e2e`로 이 REQ의 TC가 PASS인지 **확인만** 한다. 이때 바뀌는 `docs/e2e-test.md`·`docs/prd.md`·`docs/evidence/`는 PR에 넣지 않는다 (`git checkout docs/e2e-test.md docs/prd.md && git clean -fd docs/evidence`) — 여러 PR이 같은 표를 고쳐 충돌하므로, **기록 커밋은 main에서** 한다 (`docs/pipeline.md` 5단계, `/submit`). PR 본문에는 `make e2e` 요약 줄과 TC 결과를 붙인다.
   - 수동 시험 TC는 명령·결과를 `docs/e2e-test.md`에 직접 적어 PR에 넣는다.
   - FAIL이 있으면 고친다. 못 고치면 사용자에게 알리고 REQ를 `구현됨-미검증`으로 둔다 (테스트를 지우거나 skip으로 숨기지 않는다).
   - `docs/arch.md` "REQ별 코드 위치", 보안 해당 시 `docs/security-compliance.md`.
   - AI가 틀려서 고친 일이 있었으면 `docs/development.md` "AI 활용 기록"에 한 줄.
   - `python3 scripts/check-docs.py --draft`로 끊긴 ID가 없는지 확인.
5. `reviewer` 서브에이전트로 셀프 리뷰하고 지적사항을 처리한다.
6. 커밋 후 `/pr-check`(충돌 검사) → `scripts/sync.sh`로 main 반영 → 검증 재실행 → `scripts/check-conflicts.sh` ❌ 0개.
7. `.github/pull_request_template.md` 형식으로 PR 본문 초안을 보여준다. 첫 줄 `Closes #<번호>`, REQ·TC ID와 시험 결과 요약을 넣는다.
8. 사용자 확인 후 `git push -u origin <branch>` → `gh pr create`. Claude는 머지하지 않는다.
9. 머지 후 Issue가 **completed**로 닫혔는지 확인하고, Issue 본문(또는 댓글)에 **커밋 주소와 테스트 명령·결과**를 붙이자고 안내한다 (`gh issue comment <번호> --body ...`, 사용자 확인 후).
