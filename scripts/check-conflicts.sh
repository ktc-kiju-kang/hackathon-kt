#!/usr/bin/env bash
# PR 전 충돌 검사. /pr-check 스킬과 /handoff가 사용한다.
#   1) git 충돌: 현재 브랜치를 origin/main에 합치면 충돌하는 파일
#   2) 의미 충돌: main에 이미 있거나 다른 열린 PR이 만드는 같은 화면 경로·마이그레이션 번호
#   3) 겹침 경고: 다른 열린 PR / 내 브랜치 이후 main에 머지된 커밋이 같은 파일·기능을 건드림
# 사용법: scripts/check-conflicts.sh        (종료코드 1 = 충돌 있음, 0 = 없음(경고는 있을 수 있음))
set -uo pipefail
cd "$(git rev-parse --show-toplevel)" || exit 2

BASE_REF=origin/main
git fetch -q origin main || { echo "❌ origin/main fetch 실패"; exit 2; }
branch=$(git branch --show-current)
mb=$(git merge-base HEAD "$BASE_REF")
hard=0
warn=0
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

echo "## 충돌 검사: $branch → $BASE_REF"
behind=$(git rev-list --count HEAD.."$BASE_REF")
echo "- main보다 ${behind}커밋 뒤처짐$([ "$behind" -gt 0 ] && echo ' (sync 필요)')"

# 내 변경 파일 = 커밋된 것 + 작업 중(미커밋·새 파일)
{ git diff --name-only "$mb"; git ls-files --others --exclude-standard; } | sort -u > "$tmp/mine"
added_mine() { git diff --name-only --diff-filter=A "$mb"; git ls-files --others --exclude-standard; }
added_mine | sort -u > "$tmp/mine_added"
echo "- 내 변경 파일 $(wc -l < "$tmp/mine" | tr -d ' ')개"
[ -s "$tmp/mine" ] || { echo "변경 없음"; exit 0; }

# --- 1) git 충돌 (커밋된 내용 기준) ---
echo
echo "### 1. git 충돌"
if out=$(git merge-tree --write-tree --name-only --no-messages "$BASE_REF" HEAD 2>&1); then
  echo "✅ 없음"
else
  echo "$out" | tail -n +2 | sed '/^$/d' > "$tmp/conflicts"
  if [ -s "$tmp/conflicts" ]; then
    echo "❌ main과 합치면 충돌:"
    sed 's/^/  - /' "$tmp/conflicts"
    hard=1
  else
    echo "⚠️ merge-tree 실패: $out"; warn=1
  fi
fi
[ -n "$(git status --porcelain)" ] && echo "  (미커밋 변경은 이 검사에 포함되지 않음 — 커밋 후 다시 실행)"

# --- 열린 PR들의 변경 파일 ---
gh pr list --state open --json number,headRefName,author,title \
  -q ".[] | select(.headRefName != \"$branch\") | \"\(.number)\t\(.author.login)\t\(.title)\"" > "$tmp/prs" 2>/dev/null || true
while IFS=$'\t' read -r n _ _; do
  [ -n "$n" ] && gh pr diff "$n" --name-only > "$tmp/pr_$n" 2>/dev/null
done < "$tmp/prs"

# --- 2) 의미 충돌: 같은 화면 경로 / 마이그레이션 번호 ---
echo
echo "### 2. 같은 경로·번호"
found=0
# 새로 만드는 화면(page.tsx)이 main에 이미 생겼거나, 다른 PR도 만드는 경우
grep -E '^frontend/src/app/.*page\.tsx$' "$tmp/mine_added" | while read -r f; do
  if git cat-file -e "$BASE_REF:$f" 2>/dev/null; then
    echo "❌ 화면 경로 $f 가 이미 main에 있음 (누군가 먼저 머지) → 경로 분리 또는 담당자와 상의"
    echo x >> "$tmp/hard"
  fi
  for p in "$tmp"/pr_*; do
    [ -f "$p" ] && grep -qx "$f" "$p" && echo "❌ 화면 경로 $f 를 PR #${p##*_} 도 만듦" && echo x >> "$tmp/hard"
  done
done
# 새 마이그레이션 번호가 main/다른 PR과 겹치는 경우
grep -E '^database/migrations/[0-9]{4}_.*\.sql$' "$tmp/mine_added" | while read -r f; do
  num=$(basename "$f" | cut -c1-4)
  other=$(git ls-tree --name-only "$BASE_REF" database/migrations/ | grep "/${num}_" | grep -vx "$f")
  [ -n "$other" ] && echo "❌ 마이그레이션 번호 $num 이 main의 $other 와 겹침 → 내 파일 번호를 올린다" && echo x >> "$tmp/hard"
  for p in "$tmp"/pr_*; do
    [ -f "$p" ] && o=$(grep -E "^database/migrations/${num}_" "$p" | grep -vx "$f") && \
      echo "❌ 마이그레이션 번호 $num 을 PR #${p##*_} 도 사용 ($o) → 늦게 머지하는 쪽이 번호를 올린다" && echo x >> "$tmp/hard"
  done
done
[ -s "$tmp/hard" ] && hard=1 || echo "✅ 없음"

# --- 3) 겹침 경고 ---
echo
echo "### 3. 다른 작업과 겹침 (경고)"
feature_of() {  # 파일 경로 → 기능 이름 (기능 폴더·기능 파일 규칙 기준)
  sed -nE \
    -e 's#^frontend/src/features/([^/]+)/.*#\1#p' \
    -e 's#^frontend/src/app/([^/(]+)/.*#\1#p' \
    -e 's#^backend/app/(routers|services|schemas)/([a-z0-9_]+)\.py$#\2#p' \
    -e 's#^backend/app/agent/tools/([a-z0-9_]+)\.py$#tool:\1#p' \
    -e 's#^docs/contracts/([a-z0-9_-]+)\.md$#\1#p'
}
feature_of < "$tmp/mine" | grep -vE '^(__init__|README)$' | sort -u > "$tmp/my_features"

# 3-a) 열린 PR과 같은 파일·기능
while IFS=$'\t' read -r n author title; do
  [ -f "$tmp/pr_$n" ] || continue
  same=$(comm -12 "$tmp/mine" <(sort -u "$tmp/pr_$n"))
  feats=$(comm -12 "$tmp/my_features" <(feature_of < "$tmp/pr_$n" | sort -u))
  if [ -n "$same" ] || [ -n "$feats" ]; then
    warn=1
    echo "⚠️ PR #$n ($author) \"$title\""
    [ -n "$same" ] && echo "$same" | sed 's/^/    같은 파일: /'
    [ -n "$feats" ] && echo "$feats" | sed 's/^/    같은 기능: /'
  fi
done < "$tmp/prs"

# 3-b) 내 브랜치 이후 main에 머지된 커밋이 같은 파일을 건드림 (리베이스 후 동작 확인 필요)
since=$(git diff --name-only "$mb" "$BASE_REF" | sort -u)
touched=$(comm -12 "$tmp/mine" <(echo "$since"))
if [ -n "$touched" ]; then
  warn=1
  echo "⚠️ 내 브랜치 이후 main에서도 바뀐 파일 (sync 후 테스트로 확인):"
  echo "$touched" | while read -r f; do
    who=$(git log --format='%an' "$mb..$BASE_REF" -- "$f" | sort -u | paste -sd, -)
    echo "    $f ($who)"
  done
fi
[ "$warn" -eq 0 ] && echo "✅ 없음"

echo
if [ "$hard" -eq 1 ]; then
  echo "결과: ❌ 충돌 있음 — PR 전에 해결 필요"
  exit 1
fi
echo "결과: ✅ 충돌 없음$([ "$warn" -eq 1 ] && echo ' (경고 확인)')"
exit 0
