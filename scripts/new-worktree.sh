#!/usr/bin/env bash
# 사용법: scripts/new-worktree.sh <member> <task-id> <설명>
# 예:     scripts/new-worktree.sh a T-003 login-api
set -euo pipefail
[ $# -lt 3 ] && { echo "usage: $0 <member> <task-id> <desc>"; exit 1; }
member=$1; task=$2; desc=$3
root=$(git rev-parse --show-toplevel)
branch="$member/$task-$desc"
dir="$(dirname "$root")/$(basename "$root")-wt-$member-$task"

git -C "$root" fetch origin main 2>/dev/null || true
base=$(git -C "$root" rev-parse --verify -q origin/main >/dev/null && echo origin/main || echo main)
git -C "$root" worktree add -b "$branch" "$dir" "$base"
[ -f "$root/.env" ] && cp "$root/.env" "$dir/.env"
[ -f "$root/CLAUDE.local.md" ] && cp "$root/CLAUDE.local.md" "$dir/"
echo "✅ worktree: $dir  (branch: $branch)"
echo "   cd \"$dir\" && claude"
