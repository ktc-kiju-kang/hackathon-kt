---
name: submit
description: 제출 단계 — 열린 PR 정리, make record로 최종 시험 기록, 문서 마무리, 문서 strict 검사, make submit-check로 포털에 넣을 40자 SHA 확인, 발표자료 체크리스트. 개발을 마치고 제출할 때 사용.
disable-model-invocation: true
---
제출을 준비한다 (파이프라인 6단계, `docs/pipeline.md`).

1. `gh pr list`로 열린 PR을 확인한다. 각 작성자가 `make ship`으로 마무리하거나, 못 끝낸 것은 닫고 REQ를 `구현됨-미검증`·`제외(이유)`로 남긴다 (사용자가 정한다). `make lock-status`로 머지 중인 사람이 없는지 확인.
2. `make record` — main 최신 코드로 시험하고 기록을 자동 PR로 머지한다. 실패가 있으면 원인을 보고한다. 고칠지 / 해당 REQ를 `구현됨-미검증`·`제외(이유)`로 정직하게 남길지 사용자가 정한다. **실패를 PASS로 바꾸거나 테스트를 지워서 통과시키지 않는다.**
3. 실패를 고쳤으면 그 수정을 `make ship`으로 머지하고 `make record`를 다시 한다.
4. 문서 마무리 (브랜치 `docs/final-<설명>` → `make ship`): `README.md` "결과 한눈에" 숫자를 실제 표에서 센 값으로, `development.md` 효과·한계, `security-compliance.md` 요약. `python3 scripts/check-docs.py` (strict) 오류 0.
   - 문서만 바뀐 커밋은 시험 근거를 무효로 만들지 않는다 (`submit-check`는 근거 이후 `docs/`·`*.md` 밖 변경만 본다).
5. `make submit-check` — 4개 항목 모두 ✓이면 출력된 SHA를 사용자에게 보여 준다. 포털 입력은 사람이 한다: GitHub에서 그 커밋이 보이는지 → 포털 '본선 제출'에 SHA·설명 저장 → '소스 제출 완료'.
6. 발표자료 체크 (7분): 문제와 접근 / 실제 결과 화면(캡처) / AI 활용과 사람이 확인·수정한 사례(`development.md` "AI 활용 기록") / 효과와 한계(구현 vs 계획 구분). PDF·PPTX 업로드 후 새로고침해서 열리는지 확인.
7. 제출 뒤 코드를 고치면 `make ship` → `make record` → `make submit-check`를 다시 하고 새 SHA로 다시 제출한다.
