---
description: 작업 마무리 — 셀프리뷰, status 갱신, PR 준비
---
1. `git diff main...HEAD`를 `reviewer` 서브에이전트로 리뷰하고 지적사항을 처리한다.
2. 테스트/빌드 명령(CLAUDE.md 참고)이 있으면 실행한다.
3. 해당 `tasks/T-xxx-*.md` 상태를 review로, 완료 조건 체크.
4. `docs/status/<member>.md` 갱신 (다음 할 일, 막힌 것).
5. `scripts/sync.sh`로 main 반영 후 커밋.
6. `.github/pull_request_template.md` 형식으로 PR 본문 초안을 작성한다. push/PR 생성은 사용자 확인 후 진행.
