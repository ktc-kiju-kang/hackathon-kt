#!/usr/bin/env bash
# GitHub 이슈(티켓) 큐: 후보 조회 · 선점(claim) · 내 티켓 · 댓글 조회 · 해제. /ticket-loop 스킬이 사용한다.
#   scripts/ticket-claim.sh list                       작업 가능한 이슈 번호 (오래된 순, 한 줄에 하나)
#   scripts/ticket-claim.sh claim <번호> [--dry-run]    선점 시도. 종료코드 0=내가 선점, 1=졌거나 대상 아님, 2=오류
#   scripts/ticket-claim.sh mine                       내(이 에이전트)가 선점해 진행 중인 열린 이슈 번호
#   scripts/ticket-claim.sh comments <번호> [ISO시각]    신뢰 작성자의 이슈 댓글만 JSON 한 줄씩. 시각 생략 시 내 마지막 활동 이후
#   scripts/ticket-claim.sh pr-comments <PR번호>        신뢰 작성자의 PR 댓글·리뷰 코멘트만 JSON 한 줄씩
#   scripts/ticket-claim.sh release <번호> [라벨]        내 담당·in-progress·선점 댓글 해제 (+ needs-info|needs-human|blocked)
#
# 동시성: 여러 루프(다른 PC·세션)가 같은 이슈를 잡지 않게 **댓글 id 순서**를 기준으로 쓴다.
#   1) 선점 댓글(`<!-- ticket-claim:<에이전트id> -->`)을 먼저 남긴다 → 댓글 id는 단조 증가라 전체 순서가 정해진다
#   2) 잠시 기다린 뒤 선점 댓글을 다시 읽어 **가장 오래된(id 최소) 것**이 내 것일 때만 담당·라벨을 붙인다
#   3) 졌으면 내 댓글을 지우고 물러난다. TTL(기본 600초)이 지난 고아 선점 댓글은 무시한다
#   4) 이긴 뒤 선점 댓글은 **소유 표시**로 남긴다 (`mine` 이 이것으로 내 티켓을 가려낸다). release 때 지운다
# 에이전트 id = <로그인>@<호스트 해시>. **계정·PC 하나에 루프 하나**만 돌린다 (여럿이면 TICKET_AGENT_ID 로 구분).
# 신뢰: 이슈·댓글 작성자가 OWNER/MEMBER/COLLABORATOR 가 아니면 후보·명세·선점으로 인정하지 않는다
#       (공개 저장소 프롬프트 인젝션·큐 방해 방어). 에이전트가 쓰는 댓글은 첫 줄에 `<!-- ticket-agent -->` 를 넣는다.
set -uo pipefail

CLAIM_WAIT=${CLAIM_WAIT:-8}
CLAIM_TTL=${CLAIM_TTL:-600}
LABEL_BUSY=in-progress
BLOCKING='["in-progress","needs-human","needs-info","blocked","wontfix","duplicate","invalid","question"]'
TRUSTED='["OWNER","MEMBER","COLLABORATOR"]'

die() { echo "❌ $*" >&2; exit 2; }
repo=$(gh repo view --json nameWithOwner --jq .nameWithOwner 2>/dev/null) || die "gh 로그인·저장소 확인 실패"
me=$(gh api user --jq .login 2>/dev/null) || die "gh api user 실패"
host_id=$(hostname | shasum | cut -c1-6)
agent=${TICKET_AGENT_ID:-$me@$host_id}

api() { gh api "$@"; }
num_or_die() { [[ "$1" =~ ^[0-9]+$ ]] || die "번호가 숫자가 아님: $1"; }

# 이슈 JSON (PR 제외). 실패하면 비정상 종료 (빈 목록으로 오인하지 않는다)
open_issues() {
  api --paginate "repos/$repo/issues?state=open&per_page=100" \
    --jq '.[] | select(.pull_request|not) | {number,title,author:.user.login,assoc:.author_association,assignees:[.assignees[].login],labels:[.labels[].name],created_at}' |
    jq -s '.'
}

open_prs() { gh pr list --state open --json number,headRefName,body --limit 100; }

# PRS(변수)에 열린 PR이 있는지: 브랜치명 `<type>/<번호>-…` 또는 본문 Closes #번호
pr_covers() {
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
  local issues n
  issues=$(open_issues) || die "이슈 목록을 읽지 못함"
  PRS=$(open_prs) || die "PR 목록을 읽지 못함"
  echo "$issues" | eligible_json | jq -r '.[].number' | while read -r n; do
    pr_covers "$n" || echo "$n"
  done
}

# 유효한(신뢰 작성자, TTL 이내) 선점 댓글 [{id,body,created_at}] id 오름차순
claim_comments() {
  api --paginate "repos/$repo/issues/$1/comments?per_page=100" --jq '.[] | {id,body,created_at,assoc:.author_association}' |
    jq -s --argjson ttl "$CLAIM_TTL" --argjson trusted "$TRUSTED" '
      map(select(.body|contains("<!-- ticket-claim:")))
      | map(select(.assoc as $a | $trusted|index($a)))
      | map(select((now - (.created_at|fromdateiso8601)) < $ttl))
      | sort_by(.id)'
}

# 내 선점 댓글 id 목록 (TTL 무관: 이긴 뒤에도 소유 표시로 남아 있다)
my_claim_ids() {
  api --paginate "repos/$repo/issues/$1/comments?per_page=100" --jq '.[] | {id,body}' |
    jq -rs --arg m "<!-- ticket-claim:$agent -->" '.[] | select(.body|startswith($m)) | .id'
}

cmd_claim() {
  local n=$1 dry=${2:-} cid winner issue
  num_or_die "$n"
  issue=$(open_issues | jq --argjson n "$n" '.[] | select(.number==$n)') || die "이슈 조회 실패"
  [ -n "$issue" ] || { echo "SKIP #$n: 열린 이슈가 아님"; return 1; }
  echo "$issue" | jq -s '.' | eligible_json | jq -e 'length==1' >/dev/null ||
    { echo "SKIP #$n: 담당자·차단 라벨·신뢰할 수 없는 작성자 중 하나로 대상이 아님"; return 1; }
  PRS=$(open_prs) || die "PR 목록을 읽지 못함"
  pr_covers "$n" && { echo "SKIP #$n: 이미 열린 PR이 있음"; return 1; }
  if [ "$dry" = "--dry-run" ]; then echo "DRY-RUN #$n: 선점 가능 (쓰기 없음)"; return 0; fi

  gh label create "$LABEL_BUSY" --color FBCA04 --description "에이전트·담당자가 작업 중" >/dev/null 2>&1 || true

  cid=$(api "repos/$repo/issues/$n/comments" -f body="<!-- ticket-claim:$agent -->
<!-- ticket-agent -->
🤖 작업 선점 (\`$agent\`). 같은 시각에 다른 루프가 시도하면 가장 먼저 남긴 댓글이 이깁니다." --jq .id) || die "선점 댓글 작성 실패"

  sleep "$CLAIM_WAIT"
  winner=$(claim_comments "$n" | jq -r '.[0].id // empty')
  if [ "$winner" != "$cid" ]; then
    api -X DELETE "repos/$repo/issues/comments/$cid" >/dev/null 2>&1 || true
    echo "LOST #$n: 다른 루프가 먼저 선점함 (댓글 $winner)"; return 1
  fi

  if ! gh issue edit "$n" --add-assignee "$me" >/dev/null 2>&1 || ! gh issue edit "$n" --add-label "$LABEL_BUSY" >/dev/null 2>&1; then
    # 반쪽 상태를 남기지 않는다: 내가 붙인 것만 되돌리고 선점 댓글을 지운다
    gh issue edit "$n" --remove-assignee "$me" >/dev/null 2>&1 || true
    gh issue edit "$n" --remove-label "$LABEL_BUSY" >/dev/null 2>&1 || true
    api -X DELETE "repos/$repo/issues/comments/$cid" >/dev/null 2>&1 || true
    die "#$n 담당·라벨 지정 실패 (선점 취소함)"
  fi

  # 마지막 확인: 담당자가 나 하나뿐이어야 한다 (사람이 동시에 assign 했을 수 있음)
  local assignees
  assignees=$(api "repos/$repo/issues/$n" --jq '[.assignees[].login]|sort|join(",")') || die "담당자 재확인 실패"
  if [ "$assignees" != "$me" ]; then
    gh issue edit "$n" --remove-assignee "$me" >/dev/null 2>&1 || true
    # 라벨은 담당자가 아무도 안 남았을 때만 뗀다 (다른 승자의 라벨을 지우지 않는다)
    [ -z "$(api "repos/$repo/issues/$n" --jq '[.assignees[].login]|join(",")')" ] &&
      { gh issue edit "$n" --remove-label "$LABEL_BUSY" >/dev/null 2>&1 || true; }
    api -X DELETE "repos/$repo/issues/comments/$cid" >/dev/null 2>&1 || true
    echo "LOST #$n: 다른 담당자가 동시에 지정됨"; return 1
  fi
  echo "CLAIMED #$n by $agent"; return 0
}

# 내 티켓: 열린 + in-progress + 담당자가 나 + 내 선점 댓글이 있는 이슈 (사람이 직접 잡은 이슈는 제외)
cmd_mine() {
  local n
  gh issue list --state open --assignee "$me" --label "$LABEL_BUSY" --json number --jq '.[].number' | while read -r n; do
    [ -n "$(my_claim_ids "$n")" ] && echo "$n"
  done
}

cmd_comments() {
  local n=$1 since=${2:-}
  num_or_die "$n"
  if [ -z "$since" ]; then # 내 마지막 활동(선점·진행 댓글) 이후
    since=$(api --paginate "repos/$repo/issues/$n/comments?per_page=100" --jq '.[] | {created_at,body,login:.user.login}' |
      jq -rs --arg m "<!-- ticket-claim:$agent -->" 'map(select((.body|contains("<!-- ticket-agent -->")) or (.body|startswith($m)))) | map(.created_at) | max // "1970-01-01T00:00:00Z"')
  fi
  api --paginate "repos/$repo/issues/$n/comments?per_page=100" \
    --jq '.[] | {id,user:.user.login,type:.user.type,assoc:.author_association,created_at,body}' |
    jq -c --argjson trusted "$TRUSTED" --arg since "$since" '
      select(.created_at > $since)
      | select((.assoc as $a | $trusted|index($a)) and .type != "Bot")
      | select((.body|contains("<!-- ticket-claim:")|not) and (.body|contains("<!-- ticket-agent -->")|not))
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
      | select(.body|contains("<!-- ticket-agent -->")|not)
      | del(.type,.assoc)'
}

cmd_release() {
  local n=$1 state=${2:-} id
  num_or_die "$n"
  case "$state" in needs-info|needs-human|blocked|"") ;; *) die "알 수 없는 라벨: $state" ;; esac
  gh issue edit "$n" --remove-assignee "$me" >/dev/null 2>&1 || true
  gh issue edit "$n" --remove-label "$LABEL_BUSY" >/dev/null 2>&1 || true
  for id in $(my_claim_ids "$n"); do api -X DELETE "repos/$repo/issues/comments/$id" >/dev/null 2>&1 || true; done
  if [ -n "$state" ]; then
    gh label create "$state" --color D93F0B >/dev/null 2>&1 || true
    gh issue edit "$n" --add-label "$state" >/dev/null || die "#$n 에 $state 라벨을 붙이지 못함 (큐에 남을 수 있음)"
  fi
  # 해제 결과 확인: 담당자·in-progress 가 남아 있으면 실패로 본다
  if api "repos/$repo/issues/$n" --jq '[.assignees[].login]+[.labels[].name]|join(",")' | grep -Eq "(^|,)($me|$LABEL_BUSY)(,|$)"; then
    die "#$n 해제가 반영되지 않음 (담당 또는 $LABEL_BUSY 가 남아 있음)"
  fi
  echo "RELEASED #$n${state:+ → $state}"
}

case "${1:-}" in
  list)        cmd_list ;;
  claim)       [ -n "${2:-}" ] || die "사용법: claim <번호> [--dry-run]"; cmd_claim "$2" "${3:-}" ;;
  mine)        cmd_mine ;;
  comments)    [ -n "${2:-}" ] || die "사용법: comments <번호> [ISO시각]"; cmd_comments "$2" "${3:-}" ;;
  pr-comments) [ -n "${2:-}" ] || die "사용법: pr-comments <PR번호>"; cmd_pr_comments "$2" ;;
  release)     [ -n "${2:-}" ] || die "사용법: release <번호> [라벨]"; cmd_release "$2" "${3:-}" ;;
  *) sed -n '2,10p' "$0"; exit 2 ;;
esac
