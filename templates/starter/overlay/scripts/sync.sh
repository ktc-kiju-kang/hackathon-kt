#!/usr/bin/env bash
# 최신 origin/main을 현재 브랜치에 merge 한다 (rebase 대신 merge — push한 브랜치도 force push 없이 안전).
# 충돌이 나면 멈추고 파일 목록을 보여 준다. 해결 후: git add <파일> && git commit
set -euo pipefail
. "$(dirname "$0")/lib.sh"
cd "$ROOT"
[ -z "$(git status --porcelain --untracked-files=no)" ] || die "커밋 안 된 변경이 있습니다 — 커밋하거나 stash 후 다시"
git fetch -q origin main
branch=$(git branch --show-current)
if [ "$branch" = main ]; then
  git merge -q --ff-only origin/main || die "main이 origin/main과 갈라졌습니다 — main에 직접 커밋하지 마세요"
  ok "main 최신화"; exit 0
fi
before=$(git rev-parse HEAD)
if ! git merge -q --no-edit origin/main; then
  warn "충돌 파일:"; git diff --name-only --diff-filter=U | sed 's/^/    /'
  die "충돌 해결 후 git add <파일> && git commit — 남의 기능·공용 파일이면 담당자와 상의"
fi
changed=$(git diff --name-only "$before" HEAD)
[ -n "$changed" ] || { ok "이미 최신 ($branch)"; exit 0; }
ok "main 반영 ($branch)"
echo "$changed" | grep -qE '^(frontend/package(-lock)?\.json|backend/requirements.*\.txt)$' && warn "의존성이 바뀌었습니다 → make setup"
echo "$changed" | grep -q '^database/migrations/' && warn "새 마이그레이션 → 서버 재시작 시 적용 (make stop && make serve)"
echo "$changed" | grep -qE '(^|/)\.env\.example$' && warn "새 환경변수 → backend/.env, frontend/.env.local 확인"
echo "$changed" | grep -qE '^(CLAUDE\.md|\.claude/)' && warn "팀 규칙(CLAUDE.md·.claude/)이 바뀌었습니다"
exit 0
