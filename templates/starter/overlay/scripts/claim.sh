#!/usr/bin/env bash
# Issue 선점 — 같은 Issue를 두 사람이 동시에 잡지 않게 한다.
#   GitHub에 refs/heads/claim/<번호> 브랜치를 "없을 때만" 만든다 (머지 잠금과 같은 원자적 생성).
#   assignee는 여러 명이 될 수 있고 확인→등록 사이에 틈이 있어, 선점 판정은 이 ref로만 한다.
# 사용:
#   scripts/claim.sh take <번호>      선점 + 본인 assign (내 선점이면 그대로 통과)
#   scripts/claim.sh check <번호>     ship용: 내 선점인지 확인, 아무도 안 잡았으면 선점
#   scripts/claim.sh release <번호> [--force]   선점 해제 + assign 해제 (--force: 남의 선점, 주인과 얘기한 뒤만)
#   scripts/claim.sh done <번호>      머지 후 선점 ref만 지운다 (assignee는 기록으로 남김)
#   scripts/claim.sh list             누가 무엇을 잡고 있는지
set -uo pipefail
. "$(dirname "$0")/lib.sh"
command -v gh >/dev/null || die "gh CLI가 필요합니다 (gh auth login)"

CLAIM_STALE_SEC=${CLAIM_STALE_SEC:-86400}  # 24시간 넘게 활동이 없으면 list에서 경고
me=$(gh api user -q .login 2>/dev/null) || die "gh 로그인이 필요합니다 (gh auth login)"

claim_ref() { echo "refs/heads/claim/$1"; }

claim_info() {  # "<sha> <epoch> <login>" 또는 빈 값
  local ref sha
  ref=$(claim_ref "$1")
  sha=$(git -C "$ROOT" ls-remote origin "$ref" 2>/dev/null | cut -f1)
  [ -n "$sha" ] || return 0
  git -C "$ROOT" fetch -q origin "$ref" 2>/dev/null || true
  echo "$sha $(git -C "$ROOT" log -1 --format='%ct %s' "$sha" 2>/dev/null | cut -d' ' -f1-2)"
}

others_assigned() {  # 나 말고 assign된 사람 (공백 구분)
  gh issue view "$1" --json assignees -q "[.assignees[].login | select(. != \"$me\")] | join(\" \")" 2>/dev/null
}

take() {
  local n=$1 ref tree commit info owner others
  [[ "$n" =~ ^[0-9]+$ ]] || die "Issue 번호가 필요합니다: scripts/claim.sh take 12"
  gh issue view "$n" --json state -q .state 2>/dev/null | grep -q OPEN || die "Issue #$n 이 없거나 닫혀 있습니다"
  ref=$(claim_ref "$n")
  info=$(claim_info "$n")
  if [ -z "$info" ]; then
    # 웹에서 먼저 assign한 사람이 있으면 그 사람이 주인 — 선점 ref를 만들기 전에 멈춘다
    others=$(others_assigned "$n")
    [ -z "$others" ] || die "Issue #$n 은 이미 $others 님에게 배정돼 있습니다 — 다른 Issue를 고르거나 그분과 얘기하세요"
    tree=$(git -C "$ROOT" hash-object -t tree /dev/null)
    commit=$(git -C "$ROOT" commit-tree "$tree" -m "$me #$n" </dev/null)
    if ! git -C "$ROOT" push -q --force-with-lease="$ref:" origin "$commit:$ref" 2>/dev/null; then
      info=$(claim_info "$n")  # 그 몇 초 사이에 누가 먼저 잡았다
      [ -n "$info" ] || die "선점 push 실패 (권한·네트워크?) — git push 오류를 확인하세요"
    fi
  fi
  [ -n "$info" ] && { owner=$(echo "$info" | cut -d' ' -f3)
    [ "$owner" = "$me" ] || die "Issue #$n 은 $owner 님이 이미 잡았습니다 ($(ago "$info") 전) — make claims"; }
  gh issue edit "$n" --add-assignee @me >/dev/null || warn "assign 실패 — 직접 assign하세요"
  # 선점 이후에 웹에서 다른 사람이 assign했으면 알린다 (선점이 우선)
  others=$(others_assigned "$n")
  [ -z "$others" ] || warn "Issue #$n 에 $others 님도 배정돼 있습니다 — 선점은 $me. 그분께 알리세요"
  ok "Issue #$n 선점: $me"
}

check() {  # ship이 부른다. 남의 선점이거나 남에게 배정됐으면 실패
  local n=$1 info owner
  info=$(claim_info "$n")
  if [ -z "$info" ]; then take "$n"; return; fi
  owner=$(echo "$info" | cut -d' ' -f3)
  [ "$owner" = "$me" ] || die "Issue #$n 은 $owner 님이 잡은 Issue입니다 — ship 중단 (make claims)"
  ok "Issue #$n 선점 확인: $me"
}

release() {
  local n=$1 force=${2:-} info owner
  info=$(claim_info "$n")
  [ -n "$info" ] || { warn "Issue #$n 선점 없음"; return 0; }
  owner=$(echo "$info" | cut -d' ' -f3)
  if [ "$owner" != "$me" ] && [ "$force" != --force ]; then
    die "$owner 님의 선점입니다 — 주인이 확실히 손을 뗐을 때만: scripts/claim.sh release $n --force"
  fi
  git -C "$ROOT" push -q --force-with-lease="$(claim_ref "$n"):$(echo "$info" | cut -d' ' -f1)" origin ":$(claim_ref "$n")" \
    || die "선점 해제 실패"
  [ "${3:-}" = keep-assignee ] || gh issue edit "$n" --remove-assignee "$owner" >/dev/null 2>&1 || true
  ok "Issue #$n 선점 해제 ($owner)"
}

ago() {  # claim_info 줄 → 사람이 읽는 경과 시간
  local s=$(( $(date +%s) - $(echo "$1" | cut -d' ' -f2) ))
  if [ "$s" -ge 3600 ]; then echo "$((s / 3600))시간"; else echo "$((s / 60))분"; fi
}

list() {
  local rows n sha owner at last age
  rows=$(git -C "$ROOT" ls-remote origin 'refs/heads/claim/*' 2>/dev/null)
  [ -n "$rows" ] || { ok "선점된 Issue 없음"; return 0; }
  git -C "$ROOT" fetch -q --prune origin 2>/dev/null || true
  printf '  %-6s %-16s %-10s %s\n' Issue 선점 경과 "작업 브랜치(마지막 커밋)"
  while read -r sha ref; do
    n=${ref##*/}
    read -r at owner <<<"$(git -C "$ROOT" log -1 --format='%ct %s' "$sha" | cut -d' ' -f1-2)"
    # 작업 브랜치 <type>/<번호>-… 의 마지막 커밋이 있으면 그 시각을 활동으로 본다
    last=$(git -C "$ROOT" for-each-ref --sort=-committerdate --format='%(committerdate:unix) %(refname:short)' \
      "refs/remotes/origin/*/$n-*" | head -1)
    [ -n "$last" ] && at=$(echo "$last" | cut -d' ' -f1)
    age=$(( $(date +%s) - at ))
    printf '  #%-5s %-16s %-10s %s' "$n" "$owner" "$(ago "x $at")" "${last#* }"
    [ "$age" -gt "$CLAIM_STALE_SEC" ] && printf '  ⚠️ 오래 멈춤'
    echo
  done <<<"$rows"
}

cmd=${1:-list}; shift || true
case "$cmd" in
  take|check|done) [ -n "${1:-}" ] || die "Issue 번호가 필요합니다";;
esac
case "$cmd" in
  take) take "$1";;
  check) check "$1";;
  release) [ -n "${1:-}" ] || die "Issue 번호가 필요합니다"; release "$1" "${2:-}";;
  done) release "$1" --force keep-assignee;;
  list) list;;
  *) die "사용: scripts/claim.sh take|check|release|done <번호> | list";;
esac
