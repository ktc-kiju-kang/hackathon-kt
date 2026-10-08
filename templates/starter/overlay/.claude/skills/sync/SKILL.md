---
name: sync
description: 최신 origin/main을 현재 브랜치에 merge (make sync). 작업 시작 전, 중간중간, 세션 시작 시 main보다 뒤처졌을 때 사용.
---
1. `git status`로 미커밋 변경 확인. 있으면 커밋할지 stash할지 사용자에게 묻는다.
2. `make sync` 실행 (origin/main fetch + **merge** — 이미 push한 브랜치도 force push가 필요 없다).
3. 충돌 시 파일별로 양쪽 의도를 `git log -p origin/main -- <파일>`로 확인해 설명하고 해결안을 제시한다. 다른 사람의 기능 파일이나 공용 파일의 충돌은 임의로 해결하지 말고 사용자 확인을 받는다. 해결 후 `git add <파일> && git commit`.
4. `make sync`가 출력한 안내를 처리한다: 의존성 변경 → `make setup`, 새 마이그레이션 → 서버 재시작, 새 환경변수 → `.env` 확인, 규칙 변경 → `CLAUDE.md`·`.claude/` 다시 읽기. `docs/contracts/` 변경이 있으면 내 기능 영향을 요약한다.
