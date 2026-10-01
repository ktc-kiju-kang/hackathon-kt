#!/usr/bin/env bash
# 현재 브랜치에 최신 main을 rebase. 작업 시작 전 / PR 전 실행.
set -euo pipefail
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "⚠️  커밋되지 않은 변경이 있습니다. 커밋하거나 stash 후 다시 실행하세요."; exit 1
fi
if git remote | grep -q origin; then
  git fetch origin main
  git rebase origin/main
else
  git rebase main
fi
echo "✅ synced: $(git branch --show-current)"
