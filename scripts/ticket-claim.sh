#!/usr/bin/env bash
# GitHub Issue(티켓) 큐 어댑터. /ticket-loop 스킬이 쓴다. 선점은 scripts/claim.sh(git ref 원자적 생성) 하나만 기준이다.
#   scripts/ticket-claim.sh list                      작업 가능한 Issue 번호 (오래된 순, 한 줄에 하나)
#   scripts/ticket-claim.sh claim <번호> [--dry-run]   선점. 종료코드 0=내가 선점, 1=대상 아님·남이 선점, 2=오류
#   scripts/ticket-claim.sh mine                      내가 선점한 열린 Issue 번호
#   scripts/ticket-claim.sh cleanup                   내 선점 중 이슈가 닫힌 것의 선점 ref 를 정리 (머지 후 남은 claim/<번호>)
#   scripts/ticket-claim.sh comments <번호> [ISO시각]   신뢰 작성자의 Issue 댓글만 JSON 한 줄씩 (시각 생략 시 내 마지막 에이전트 댓글 이후)
#   scripts/ticket-claim.sh pr-comments <PR번호>       신뢰 작성자의 PR 댓글·리뷰 코멘트만 JSON 한 줄씩
#   scripts/ticket-claim.sh release <번호> [라벨]       선점 해제 (+ needs-info|needs-human|blocked 라벨), in-progress 라벨 제거
#   scripts/ticket-claim.sh owns <번호>                 이 세션이 잡은 티켓인가. 종료코드 0=내 세션(또는 세션 표식 없음), 1=같은 계정의 다른 세션
#   scripts/ticket-claim.sh done <번호>                 구현 완료 표기: impl-done 라벨 (PR 생성 뒤)
# claim 은 성공하면 in-progress 라벨과 세션 표식 댓글(<!-- ticket-agent session=ID -->)을 남긴다. 세션 ID 는 TICKET_SESSION, 없으면 호스트·경로 해시.
#
# 동시성: claim.sh 가 refs/heads/claim/<번호> 를 "없을 때만" 만든다 → 사람(make claims)과 루프가 같은 기준을 본다.
#   한계: 선점 주인은 **GitHub 계정** 단위다. 같은 계정으로 루프를 둘 돌리면 서로를 구분하지 못한다 (계정당 루프 하나).
# 신뢰: Issue·댓글 작성자가 OWNER/MEMBER/COLLABORATOR 가 아니면 후보·명세로 인정하지 않는다 (공개 저장소 프롬프트 인젝션 방어).
#       에이전트가 쓰는 댓글은 첫 줄에 `<!-- ticket-agent -->` 를 넣는다. `make ship` 의 근거 댓글("구현·검증 근거 (make ship)")도 함께 걸러
#       자기 댓글을 명세로 다시 읽지 않게 한다.
set -uo pipefail

BLOCKING='["in-progress","needs-human","needs-info","blocked","wontfix","duplicate","invalid","question"]'
TRUSTED='["OWNER","MEMBER","COLLABORATOR"]'
HERE=$(cd "$(dirname "$0")" && pwd)
CLAIM="$HERE/claim.sh"

die() { echo "❌ $*" >&2; exit 2; }
[ -x "$CLAIM" ] || die "scripts/claim.sh 가 없다 (main 의 시작 키트가 필요)"
repo=$(gh repo view --json nameWithOwner --jq .nameWithOwner 2>/dev/null) || die "gh 로그인·저장소 확인 실패"
me=$(gh api user --jq .login 2>/dev/null) || die "gh api user 실패"
ROOT=$(git -C "$HERE" rev-parse --show-toplevel)
# 세션 ID: 같은 계정의 다른 세션과 구분한다 (호스트명은 공개 댓글에 쓰지 않고 해시만 쓴다)
SID=${TICKET_SESSION:-$(printf '%s' "$(hostname)$(git -C "$ROOT" rev-parse --git-common-dir)" | shasum | cut -c1-8)}

api() { gh api "$@"; }
num_or_die() { [[ "$1" =~ ^[0-9]+$ ]] || die "번호가 숫자가 아님: $1"; }

# 이슈 JSON (PR 제외). 실패하면 비정상 종료 (빈 목록으로 오인하지 않는다)
open_issues() {
  api --paginate "repos/$repo/issues?state=open&per_page=100" \
    --jq '.[] | select(.pull_request|not) | {number,title,author:.user.login,assoc:.author_association,assignees:[.assignees[].login],labels:[.labels[].name],created_at}' |
    jq -s '.'
}

open_prs() { gh pr list --state open --json number,headRefName,body --limit 100; }

# 선점 ref 목록: "<번호> <소유자>" (소유자 = claim.sh 가 커밋 제목에 적는 로그인)
claims() {
  local rows sha ref
  rows=$(git -C "$ROOT" ls-remote origin 'refs/heads/claim/*' 2>/dev/null) || return 1
  [ -n "$rows" ] || return 0
  git -C "$ROOT" fetch -q origin 'refs/heads/claim/*:refs/remotes/origin/claim/*' 2>/dev/null || true
  while read -r sha ref; do
    echo "${ref##*/} $(git -C "$ROOT" log -1 --format=%s "$sha" 2>/dev/null | cut -d' ' -f1)"
  done <<<"$rows"
}

pr_covers() { # $PRS 에 열린 PR이 있는지: 브랜치명 `<type>/<번호>-…` 또는 본문 Closes #번호
  echo "$PRS" | jq -e --arg n "$1" 'map(select((.headRefName|test("/"+$n+"-")) or ((.body // "")|test("(?i)(closes|fixes|resolves)\\s+#"+$n+"\\b")))) | length > 0' >/dev/null
}

eligible_json() { # stdin: 이슈 목록 → 후보(오래된 순)
  jq --argjson blocking "$BLOCKING" --argjson trusted "$TRUSTED" '
    map(select((.assignees|length)==0
      and ((.labels|map(select(. as $l | $blocking|index($l)))|length)==0)
      and (.assoc as $a | $trusted|index($a))))
    | sort_by(.created_at)'
}

cmd_list() {
  local issues taken n
  issues=$(open_issues) || die "이슈 목록을 읽지 못함"
  PRS=$(open_prs) || die "PR 목록을 읽지 못함"
  taken=$(claims) || die "선점 목록을 읽지 못함 (git ls-remote 실패)"
  echo "$issues" | eligible_json | jq -r '.[].number' | while read -r n; do
    echo "$taken" | grep -q "^$n " && continue   # 이미 누군가 선점 (assign 전이어도)
    pr_covers "$n" || echo "$n"
  done
}

cmd_claim() {
  local n=$1 dry=${2:-} issue out rc
  num_or_die "$n"
  issue=$(open_issues | jq --argjson n "$n" '.[] | select(.number==$n)') || die "이슈 조회 실패"
  [ -n "$issue" ] || { echo "SKIP #$n: 열린 이슈가 아님"; return 1; }
  echo "$issue" | jq -s '.' | eligible_json | jq -e 'length==1' >/dev/null ||
    { echo "SKIP #$n: 담당자·차단 라벨·신뢰할 수 없는 작성자 중 하나로 대상이 아님"; return 1; }
  PRS=$(open_prs) || die "PR 목록을 읽지 못함"
  pr_covers "$n" && { echo "SKIP #$n: 이미 열린 PR이 있음"; return 1; }
  claims | grep -q "^$n " && { echo "SKIP #$n: 이미 선점됨 ($(claims | grep "^$n " | cut -d' ' -f2))"; return 1; }
  if [ "$dry" = "--dry-run" ]; then echo "DRY-RUN #$n: 선점 가능 (쓰기 없음)"; return 0; fi

  out=$("$CLAIM" take "$n" 2>&1); rc=$?
  if [ $rc -ne 0 ]; then echo "LOST #$n: $(echo "$out" | tail -1)"; return 1; fi
  # 확인: 선점 주인이 나인가 (claim.sh 는 같은 계정이면 통과시키므로 주인이 나인지만 본다)
  [ "$(claims | grep "^$n " | cut -d' ' -f2)" = "$me" ] || { echo "LOST #$n: 선점 주인이 내가 아님"; return 1; }
  gh issue edit "$n" --add-label in-progress >/dev/null 2>&1 || echo "⚠️ #$n in-progress 라벨 실패" >&2
  gh issue comment "$n" --body "<!-- ticket-agent session=$SID -->
작업 시작 (세션 \`$SID\`)" >/dev/null 2>&1 || echo "⚠️ #$n 세션 표식 댓글 실패" >&2
  echo "CLAIMED #$n by $me (session $SID)"; return 0
}

cmd_mine() {
  local n owner
  claims | while read -r n owner; do
    [ "$owner" = "$me" ] || continue
    gh issue view "$n" --json state --jq '.state' 2>/dev/null | grep -q OPEN && echo "$n"
  done
}

cmd_owns() {
  local n=$1 last
  num_or_die "$n"
  last=$(api --paginate "repos/$repo/issues/$n/comments?per_page=100" --jq '.[] | {login:.user.login,body}' |
    jq -rs --arg me "$me" 'map(select(.login==$me) | .body | capture("<!-- ticket-agent session=(?<s>[0-9A-Za-z_-]+) -->").s?) | map(select(.!=null)) | last // ""')
  [ -z "$last" ] || [ "$last" = "$SID" ] && { echo "OWNED #$n (session $SID)"; return 0; }
  echo "OTHER-SESSION #$n (session $last)"; return 1
}

cmd_done() {
  local n=$1
  num_or_die "$n"
  gh label create impl-done --color 0E8A16 --description "구현 완료, PR 리뷰 대기" >/dev/null 2>&1 || true
  gh issue edit "$n" --add-label impl-done >/dev/null || die "#$n impl-done 라벨 실패"
  echo "DONE #$n → impl-done"
}

cmd_cleanup() {
  local n owner
  claims | while read -r n owner; do
    [ "$owner" = "$me" ] || continue
    if [ "$(gh issue view "$n" --json state --jq .state 2>/dev/null)" = "CLOSED" ]; then
      "$CLAIM" done "$n" >/dev/null 2>&1 && echo "CLEANED #$n" || echo "FAILED #$n (선점 ref 정리 실패)" >&2
    fi
  done
}

cmd_comments() {
  local n=$1 since=${2:-}
  num_or_die "$n"
  if [ -z "$since" ]; then # 내 마지막 에이전트 댓글 이후 (없으면 처음부터)
    since=$(api --paginate "repos/$repo/issues/$n/comments?per_page=100" --jq '.[] | {created_at,body,login:.user.login}' |
      jq -rs --arg me "$me" 'map(select(.login==$me and (.body|contains("<!-- ticket-agent -->")))) | map(.created_at) | max // "1970-01-01T00:00:00Z"')
  fi
  api --paginate "repos/$repo/issues/$n/comments?per_page=100" \
    --jq '.[] | {id,user:.user.login,type:.user.type,assoc:.author_association,created_at,body}' |
    jq -c --argjson trusted "$TRUSTED" --arg since "$since" '
      select(.created_at > $since)
      | select((.assoc as $a | $trusted|index($a)) and .type != "Bot")
      | select((.body|contains("<!-- ticket-agent -->")|not) and (.body|startswith("구현·검증 근거 (make ship)")|not))
      | {id,user,created_at,body}'
}

cmd_pr_comments() {
  local n=$1
  num_or_die "$n"
  {
    api --paginate "repos/$repo/issues/$n/comments?per_page=100" --jq '.[] | {id,kind:"conversation",user:.user.login,type:.user.type,assoc:.author_association,created_at,body}'
    api --paginate "repos/$repo/pulls/$n/comments?per_page=100" --jq '.[] | {id,kind:"review-comment",path,user:.user.login,type:.user.type,assoc:.author_association,created_at,body}'
    api --paginate "repos/$repo/pulls/$n/reviews?per_page=100" --jq '.[] | select(.body != "") | {id,kind:"review",state,user:.user.login,type:.user.type,assoc:.author_association,created_at:.submitted_at,body}'
  } | jq -c --argjson trusted "$TRUSTED" '
      select((.assoc as $a | $trusted|index($a)) and .type != "Bot")
      | select((.body|contains("<!-- ticket-agent -->")|not) and (.body|startswith("구현·검증 근거 (make ship)")|not))
      | del(.type,.assoc)'
}

cmd_release() {
  local n=$1 state=${2:-}
  num_or_die "$n"
  case "$state" in needs-info|needs-human|blocked|"") ;; *) die "알 수 없는 라벨: $state" ;; esac
  # 내 선점일 때만 푼다 (claim.sh 가 남의 선점은 거부한다). 선점이 이미 없으면 라벨만 처리한다
  if claims | grep -q "^$n "; then
    "$CLAIM" release "$n" >/dev/null 2>&1 || die "#$n 선점 해제 실패 (남의 선점이거나 권한 문제)"
  fi
  if [ -n "$state" ]; then
    gh label create "$state" --color D93F0B >/dev/null 2>&1 || true
    gh issue edit "$n" --add-label "$state" >/dev/null || die "#$n 에 $state 라벨을 붙이지 못함 (큐에 남을 수 있음)"
  fi
  gh issue edit "$n" --remove-label in-progress >/dev/null 2>&1 || true
  claims | grep -q "^$n " && die "#$n 선점이 남아 있음"
  echo "RELEASED #$n${state:+ → $state}"
}

case "${1:-}" in
  list)        cmd_list ;;
  claim)       [ -n "${2:-}" ] || die "사용법: claim <번호> [--dry-run]"; cmd_claim "$2" "${3:-}" ;;
  mine)        cmd_mine ;;
  cleanup)     cmd_cleanup ;;
  comments)    [ -n "${2:-}" ] || die "사용법: comments <번호> [ISO시각]"; cmd_comments "$2" "${3:-}" ;;
  pr-comments) [ -n "${2:-}" ] || die "사용법: pr-comments <PR번호>"; cmd_pr_comments "$2" ;;
  owns)        [ -n "${2:-}" ] || die "사용법: owns <번호>"; cmd_owns "$2" ;;
  done)        [ -n "${2:-}" ] || die "사용법: done <번호>"; cmd_done "$2" ;;
  release)     [ -n "${2:-}" ] || die "사용법: release <번호> [라벨]"; cmd_release "$2" "${3:-}" ;;
  *) sed -n '2,12p' "$0"; exit 2 ;;
esac
