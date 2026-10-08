#!/usr/bin/env bash
# /ticket-loop 사전 점검 — 토큰을 쓰지 않는 결정적 검사. 할 일이 있을 때만 에이전트 틱을 돌리게 한다.
#   scripts/ticket-loop-precheck.sh
# 출력: 첫 줄 `IDLE` 또는 `WORK`, 이어서 이유 (한 줄에 하나). 종료코드 0=IDLE, 10=WORK, 2=오류.
# WORK 조건: ① 새 티켓 후보가 있다 ② 내 티켓에 새 신뢰 댓글이 있다
#            ③ 내 티켓의 PR이 머지 없이 닫혔거나 체크가 실패했다 (머지된 티켓은 cleanup 이 정리한다)
# agent-pause 라벨이 있는 열린 Issue 가 있으면 항상 IDLE.
set -uo pipefail
# GitHub 연결이 멈추면 3분마다 프로세스가 쌓이므로 90초 안에 끝나지 않으면 스스로 중단한다 (macOS 에는 timeout 이 없다).
if [ -z "${PRECHECK_INNER:-}" ]; then
  # 자식은 자기 프로세스 그룹·임시 파일 출력으로 돌려, 시간 초과 시 그룹째 죽이고 멈춘 gh 가 출력 파이프를 붙잡지 않게 한다
  PRECHECK_INNER=1 exec perl -e '$t = "/tmp/ticket-precheck.$$"; $p = fork; if (!$p) { setpgrp(0, 0); open STDOUT, ">", $t; open STDERR, ">&STDOUT"; exec @ARGV } $SIG{ALRM} = sub { kill "TERM", -$p; unlink $t; print "ERROR 사전 점검 시간 초과(" . ($ENV{PRECHECK_TIMEOUT} || 90) . "초) — GitHub 연결 확인\n"; exit 2 }; alarm($ENV{PRECHECK_TIMEOUT} || 90); waitpid $p, 0; $c = $? >> 8; if (open F, $t) { print <F>; close F } unlink $t; exit $c' "$0" "$@"
fi
HERE=$(cd "$(dirname "$0")" && pwd)
T="$HERE/ticket-claim.sh"
err() { echo "ERROR $*"; exit 2; }

paused=$(gh issue list --label agent-pause --state open --json number --jq 'length') || err "agent-pause 조회 실패"
[ "$paused" = 0 ] || { echo "IDLE"; echo "agent-pause 라벨이 붙은 Issue 가 있어 정지 중"; exit 0; }

"$T" cleanup >/dev/null 2>&1
list=$("$T" list) || err "list 실패"
mine=$("$T" mine) || err "mine 실패"
prs=$(gh pr list --state all --limit 100 --json number,state,headRefName,body) || err "PR 목록 조회 실패"

reasons=()
[ -n "$list" ] && reasons+=("새 티켓 후보: $(echo $list)")
for n in $mine; do
  c=$("$T" comments "$n") || err "#$n comments 실패"
  [ -n "$c" ] && reasons+=("#$n 새 댓글 $(echo "$c" | wc -l | tr -d ' ')건")
  pr=$(echo "$prs" | jq -r --arg n "$n" '[.[] | select((.headRefName|test("/"+$n+"-")) or ((.body // "")|test("(?i)(closes|fixes|resolves)\\s+#"+$n+"\\b")))] | sort_by(-.number) | .[0] // empty | "\(.number) \(.state)"')
  [ -n "$pr" ] || continue
  num=${pr% *}; state=${pr#* }
  case "$state" in
    CLOSED) reasons+=("#$n PR #$num 이 머지 없이 닫힘") ;;
    OPEN)
      if gh pr checks "$num" 2>/dev/null | awk -F'\t' '{print $2}' | grep -qx "fail"; then
        reasons+=("#$n PR #$num 체크 실패")
      fi ;;
  esac
done

if [ ${#reasons[@]} -eq 0 ]; then echo "IDLE"; [ -n "$mine" ] && echo "진행 중: $(echo $mine) (새 댓글·실패 없음)"; exit 0; fi
echo "WORK"; printf '%s\n' "${reasons[@]}"; exit 10
