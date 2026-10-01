---
name: sync
description: 최신 origin/main을 현재 브랜치에 rebase. 작업 시작 전, PR 전, 세션 시작 시 main보다 뒤처졌을 때 사용.
---
1. `git status`로 미커밋 변경 확인. 있으면 커밋할지 stash할지 사용자에게 묻는다.
2. `scripts/sync.sh` 실행 (origin/main fetch + rebase).
3. 충돌 시 파일별로 양쪽 의도를 설명하고 해결안을 제시한다. 다른 멤버 소유 파일의 충돌은 임의로 해결하지 말고 사용자 확인을 받는다.
4. 반영된 main 변경 중 다음이 있으면 요약해서 알린다:
   - `docs/CONTRACTS.md` (계약 변경 → 내 코드 영향 확인)
   - `web/package.json`, `api/requirements*.txt` (의존성 변경 → `npm install` / `pip install -r requirements-dev.txt` 안내)
   - `CLAUDE.md`, `.claude/` (규칙 변경)
5. rebase 후 이미 push된 브랜치라면 `git push --force-with-lease`가 필요하다고 안내하고, 실행은 사용자 확인 후.
