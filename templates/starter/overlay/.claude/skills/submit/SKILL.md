---
name: submit
description: 제출 단계 — main 최신화, make e2e로 최종 시험 기록, 문서 strict 검사, make submit-check로 포털에 넣을 40자 SHA 확인, 발표자료 체크리스트. 개발을 마치고 제출할 때 사용.
disable-model-invocation: true
---
제출을 준비한다 (파이프라인 6단계, `docs/pipeline.md`).

1. `git switch main && git pull --ff-only`. 열린 PR이 있으면 머지할지 사용자에게 묻는다 (`gh pr list`). 머지는 사람이 한다.
2. `make e2e` — 실패가 있으면 멈추고 원인을 보고한다. 고칠지 / 해당 REQ를 `구현됨-미검증`·`제외(이유)`로 정직하게 남길지 사용자가 정한다. **실패를 PASS로 바꾸거나 테스트를 지워서 통과시키지 않는다.**
3. 결과 커밋: `docs/e2e-test.md`, `docs/prd.md`, `docs/evidence/` → 브랜치 `docs/final-evidence` → PR → 머지 (main 보호가 없으면 사용자 확인 후 main에 직접).
4. 문서 마무리: `README.md` "결과 한눈에" 숫자를 실제 표에서 센 값으로, `development.md` 효과·한계, `security-compliance.md` 요약. `python3 scripts/check-docs.py` (strict) 오류 0.
   - 문서만 바뀐 커밋은 시험 근거를 무효로 만들지 않는다 (`submit-check`가 근거 이후 `docs/` 밖 변경만 본다).
5. `make submit-check` — 4개 항목 모두 ✓이면 출력된 SHA를 사용자에게 보여 준다. 포털 입력은 사람이 한다: GitHub에서 그 커밋이 보이는지 → 포털 '본선 제출'에 SHA·설명 저장 → '소스 제출 완료'.
6. 발표자료 체크 (7분): 문제와 접근 / 실제 결과 화면(캡처) / AI 활용과 사람이 확인·수정한 사례(`development.md` "AI 활용 기록") / 효과와 한계(구현 vs 계획 구분). PDF·PPTX 업로드 후 새로고침해서 열리는지 확인.
7. 제출 뒤 코드를 고치면 `make e2e` → 커밋 → `make submit-check`를 다시 하고 새 SHA로 다시 제출한다.
