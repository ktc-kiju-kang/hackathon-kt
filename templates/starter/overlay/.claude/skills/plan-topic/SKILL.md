---
name: plan-topic
description: 기획 단계 — 공개된 주제(원문 붙여넣기·파일)를 문제 정의·REQ/AC·TC 시나리오·보안(SEC) 매핑·Issue 분할·일정으로 바꿔 project-brief.md·prd.md·e2e-test.md·security-compliance.md 초안을 쓴다. 주제가 공개됐을 때, 범위를 다시 잡을 때 사용.
argument-hint: <주제 원문 또는 파일 경로>
disable-model-invocation: true
---
주제를 기획으로 바꾼다: $ARGUMENTS  (파이프라인 1단계, `docs/pipeline.md`)

1. **읽기** — 주제 원문(필수 범위·완료 조건·제약), `docs/security-policy.md`(SEC 항목), 남은 시간(마감 2026-10-15 00:00)을 확인한다. 애매한 요구는 추측하지 말고 **질문 목록**으로 정리해 사용자에게 묻는다.
2. **문제 정의** → `docs/project-brief.md`: 대상 사용자, 지금의 불편, 목표와 측정 방법, 범위(주최 필수 / 팀 추가 구분), 제약·가정, 팀 분담 초안.
3. **요구사항** → `docs/prd.md`:
   - 주최 요구는 REQ-01부터(출처 `주최`), 팀 아이디어는 REQ-11부터(출처 `팀`). 하나의 REQ = 한 사람이 반나절 안에 frontend+backend+시험까지 끝낼 크기. 크면 쪼갠다.
   - REQ마다 AC를 **관찰 가능한 결과**로: 정상 1개 이상 + 오류 1개 + (데이터가 사용자별이면) 권한 경계 1개.
   - 필수 범위가 시간 안에 안 되면 지금 `제외(이유)`로 적자고 제안한다 — 마지막에 숨기는 것보다 낫다.
4. **시험 설계** → `docs/e2e-test.md` "시험 목록"·"시험 상세": AC마다 TC를 GIVEN/WHEN/THEN으로, 상태 `미실행`. 방식(backend 테스트 / e2e / 수동)을 정하고, 자동 시험은 테스트 이름에 넣을 TC ID를 적는다 (`test_tc_01_3_...`).
5. **보안 매핑** → `docs/security-compliance.md`: 정책의 SEC를 **그대로** 옮기고, 각 SEC가 어느 REQ·코드에 해당하는지 또는 `해당 없음(이유)`. 해당하는 SEC는 TC-Sxx-n을 만든다.
6. **설계 초안** → `docs/arch.md`: 화면·API·테이블 목록과 REQ 연결 (구현 전이라 코드 위치는 비워 둔다).
7. **Issue 분할·일정** — REQ별 Issue 목록(제목 `[REQ-01] …`), 담당자 3명 배정안(같은 파일을 두 사람이 건드리지 않게 기능 단위로), 의존 순서, `docs/pipeline.md` 시간표에 맞춘 일정. 표로 보여 준다.
8. **게이트** — `python3 scripts/check-docs.py --draft` 오류 0을 확인하고, 질문 목록·범위·분담을 사용자에게 보여 확인받는다. 확인 후 `/new-issue`로 Issue를 만든다 (생성은 사용자 확인 후, 여러 개면 목록으로 한 번에 확인).
9. 기획에서 AI가 낸 안을 팀이 바꾼 것은 `docs/development.md` "결정과 변경" / "AI 활용 기록"에 남긴다.
