#!/usr/bin/env bash
# Claude Code SessionStart 훅: 세션 시작 시 컨텍스트 주입
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" || exit 0
branch=$(git branch --show-current 2>/dev/null)
echo "## 세션 컨텍스트"
echo "- 브랜치: ${branch:-?}"
[ "$branch" = "main" ] && echo "- ⚠️ main 브랜치입니다. 작업은 /start-task <이슈번호> 로 브랜치를 만드세요."
if git rev-parse --verify -q origin/main >/dev/null; then
  git fetch -q origin main 2>/dev/null || true
  behind=$(git rev-list --count HEAD..origin/main 2>/dev/null || echo 0)
  [ "$behind" -gt 0 ] && echo "- ⚠️ origin/main보다 ${behind}커밋 뒤처짐 → /sync 권장"
fi
dirty=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
[ "$dirty" -gt 0 ] && echo "- 미커밋 변경 ${dirty}개"

if command -v gh >/dev/null 2>&1; then
  echo
  echo "## 내 이슈 (open, assignee=@me)"
  gh issue list --assignee @me --state open --limit 10 2>/dev/null || echo "(gh 조회 실패)"
  echo
  echo "## 열린 PR"
  gh pr list --state open --limit 10 2>/dev/null || echo "(gh 조회 실패)"
fi
exit 0
