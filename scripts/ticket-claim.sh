#!/usr/bin/env bash
# GitHub 이슈(티켓) 큐: 후보 조회 · 선점(claim) · 댓글 조회 · 해제. /ticket-loop 스킬이 사용한다.
#   scripts/ticket-claim.sh list                      작업 가능한 이슈 번호 (오래된 순, 한 줄에 하나)
#   scripts/ticket-claim.sh claim <번호> [--dry-run]   선점 시도. 종료코드 0=내가 선점, 1=졌거나 대상 아님, 2=오류
#   scripts/ticket-claim.sh comments <번호> [ISO시각]   신뢰할 수 있는 작성자의 댓글만 JSON 한 줄씩 (시각 이후)
#   scripts/ticket-claim.sh release <번호> [라벨]       내 담당·in-progress 해제 (+ needs-info|needs-human|blocked)
#
# 동시성: 여러 루프(다른 PC·세션)가 같은 이슈를 잡지 않게 **댓글을 순서 기준**으로 쓴다.
#   1) 선점 댓글(`<!-- ticket-claim:… -->`)을 먼저 남긴다 → 댓글 id는 단조 증가라 전체 순서가 정해진다
#   2) 잠시 기다린 뒤 선점 댓글을 다시 읽어 **가장 오래된(id 최소) 것**이 내 것일 때만 담당·라벨을 붙인다
#   3) 졌으면 내 댓글을 지우고 물러난다. TTL(기본 600초)이 지난 고아 선점 댓글은 무시한다
# 신뢰: 이슈·댓글 작성자가 OWNER/MEMBER/COLLABORATOR 가 아니면 후보·명세로 쓰지 않는다 (공개 저장소 프롬프트 인젝션 방어).
set -uo pipefail

CLAIM_WAIT=${CLAIM_WAIT:-8}
CLAIM_TTL=${CLAIM_TTL:-600}
LABEL_BUSY=in-progress
BLOCKING='["in-progress","needs-human","needs-info","blocked","wontfix","duplicate","invalid","question"]'
TRUSTED='["OWNER","MEMBER","COLLABORATOR"]'

repo=$(gh repo view --json nameWithOwner --jq .nameWithOwner 2>/dev/null) || { echo "❌ gh 로그인·저장소 확인 실패" >&2; exit 2; }
me=$(gh api user --jq .login 2>/dev/null) || { echo "❌ gh api user 실패" >&2; exit 2; }
agent="$me@$(hostname -s):$$"

api() { gh api "$@"; }

# 이슈 JSON (PR 제외). 필드: number title body user author_association assignees labels created_at
open_issues() {
  api --paginate "repos/$repo/issues?state=open&per_page=100" \
    --jq '.[] | select(.pull_request|not) | {number,title,author:.user.login,assoc:.author_association,assignees:[.assignees[].login],labels:[.labels[].name],created_at}' |
    jq -s '.'
}

# 열린 PR이 이미 이 이슈를 다루는지 (브랜치명 `<type>/<번호>-…` 또는 본문 Closes #번호)
has_open_pr() {
  local n=$1
  gh pr list --state open --json number,headRefName,body --limit 100 |
    jq -e --arg n "$n" 'map(select((.headRefName|test("/"+$n+"-")) or ((.body // "")|test("(?i)(closes|fixes|resolves)\\s+#"+$n+"\\b")))) | length > 0' >/dev/null
}

eligible_json() { # stdin: open_issues → 후보 목록(오래된 순)
  jq --argjson blocking "$BLOCKING" --argjson trusted "$TRUSTED" '
    map(select((.assignees|length)==0
      and ((.labels|map(select(. as $l | $blocking|index($l)))|length)==0)
      and (.assoc as $a | $trusted|index($a))))
    | sort_by(.created_at)'
}

cmd_list() {
  local n
  open_issues | eligible_json | jq -r '.[].number' | while read -r n; do
    has_open_pr "$n" || echo "$n"
  done
}

claim_comments() { # 유효한(TTL 이내) 선점 댓글 [{id,body,created_at}] id 오름차순
  api --paginate "repos/$repo/issues/$1/comments?per_page=100" --jq '.[] | {id,body,created_at}' |
    jq -s --argjson ttl "$CLAIM_TTL" '
      map(select(.body|contains("<!-- ticket-claim:")))
      | map(select((now - (.created_at|fromdateiso8601)) < $ttl))
      | sort_by(.id)'
}

cmd_claim() {
  local n=$1 dry=${2:-} cid winner
  local issue
  issue=$(open_issues | jq --argjson n "$n" '.[] | select(.number==$n)') || return 2
  [ -n "$issue" ] || { echo "SKIP #$n: 열린 이슈가 아님" ; return 1; }
  echo "$issue" | jq -s 'map(.)' | eligible_json | jq -e 'length==1' >/dev/null ||
    { echo "SKIP #$n: 담당자·차단 라벨·신뢰할 수 없는 작성자 중 하나로 대상이 아님"; return 1; }
  has_open_pr "$n" && { echo "SKIP #$n: 이미 열린 PR이 있음"; return 1; }
  if [ "$dry" = "--dry-run" ]; then echo "DRY-RUN #$n: 선점 가능 (쓰기 없음)"; return 0; fi

  gh label create "$LABEL_BUSY" --color FBCA04 --description "에이전트·담당자가 작업 중" >/dev/null 2>&1 || true

  cid=$(api "repos/$repo/issues/$n/comments" -f body="<!-- ticket-claim:$agent -->
🤖 작업 선점 시도 (\`$agent\`). 같은 시각에 다른 루프가 시도하면 가장 먼저 남긴 댓글이 이깁니다." --jq .id) || return 2

  sleep "$CLAIM_WAIT"
  winner=$(claim_comments "$n" | jq -r '.[0].id // empty')
  if [ "$winner" != "$cid" ]; then
    api -X DELETE "repos/$repo/issues/comments/$cid" >/dev/null 2>&1 || true
    echo "LOST #$n: 다른 루프가 먼저 선점함 (댓글 $winner)"; return 1
  fi

  gh issue edit "$n" --add-assignee "$me" --add-label "$LABEL_BUSY" >/dev/null || return 2
  # 마지막 확인: 담당자가 나 하나뿐이어야 한다 (사람이 동시에 assign 했을 수 있음)
  if [ "$(api "repos/$repo/issues/$n" --jq '[.assignees[].login]|sort|join(",")')" != "$me" ]; then
    gh issue edit "$n" --remove-assignee "$me" --remove-label "$LABEL_BUSY" >/dev/null 2>&1 || true
    api -X DELETE "repos/$repo/issues/comments/$cid" >/dev/null 2>&1 || true
    echo "LOST #$n: 다른 담당자가 동시에 지정됨"; return 1
  fi
  echo "CLAIMED #$n by $agent"; return 0
}

cmd_comments() {
  local n=$1 since=${2:-1970-01-01T00:00:00Z}
  api --paginate "repos/$repo/issues/$n/comments?per_page=100" \
    --jq '.[] | {id,user:.user.login,type:.user.type,assoc:.author_association,created_at,body}' |
    jq -c --argjson trusted "$TRUSTED" --arg since "$since" '
      select(.created_at > $since)
      | select((.assoc as $a | $trusted|index($a)) and .type != "Bot")
      | select(.body|contains("<!-- ticket-claim:")|not)
      | {id,user,created_at,body}'
}

cmd_release() {
  local n=$1 state=${2:-}
  gh issue edit "$n" --remove-assignee "$me" --remove-label "$LABEL_BUSY" >/dev/null 2>&1 || true
  case "$state" in
    needs-info|needs-human|blocked)
      gh label create "$state" --color D93F0B >/dev/null 2>&1 || true
      gh issue edit "$n" --add-label "$state" >/dev/null ;;
    "") ;;
    *) echo "❌ 알 수 없는 라벨: $state" >&2; return 2 ;;
  esac
  echo "RELEASED #$n ${state:+→ $state}"
}

case "${1:-}" in
  list)     cmd_list ;;
  claim)    [ -n "${2:-}" ] || { echo "사용법: claim <번호> [--dry-run]" >&2; exit 2; }; cmd_claim "$2" "${3:-}" ;;
  comments) [ -n "${2:-}" ] || { echo "사용법: comments <번호> [ISO시각]" >&2; exit 2; }; cmd_comments "$2" "${3:-}" ;;
  release)  [ -n "${2:-}" ] || { echo "사용법: release <번호> [라벨]" >&2; exit 2; }; cmd_release "$2" "${3:-}" ;;
  *) sed -n '2,10p' "$0"; exit 2 ;;
esac
