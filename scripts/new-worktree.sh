#!/usr/bin/env bash
# 동시에 여러 이슈를 작업할 때 이슈별 worktree 생성.
# 사용법: scripts/new-worktree.sh <이슈번호> <설명> [type=feat]
# 예:     scripts/new-worktree.sh 12 login-page
set -euo pipefail
[ $# -lt 2 ] && { echo "usage: $0 <issue#> <desc> [type]"; exit 1; }
issue=$1; desc=$2; type=${3:-feat}
root=$(git rev-parse --show-toplevel)
branch="$type/$issue-$desc"
dir="$(dirname "$root")/$(basename "$root")-wt-$issue"

git -C "$root" fetch origin main 2>/dev/null || true
base=$(git -C "$root" rev-parse --verify -q origin/main >/dev/null && echo origin/main || echo main)
git -C "$root" worktree add -b "$branch" "$dir" "$base"
for f in frontend/.env.local backend/.env CLAUDE.local.md; do
  [ -f "$root/$f" ] && cp "$root/$f" "$dir/$f"
done
echo "✅ worktree: $dir  (branch: $branch)"
echo "   cd \"$dir\" && claude"
