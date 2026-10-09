#!/usr/bin/env bash
# /ticket-loop 한 틱의 결정적인 앞부분 — 킬 스위치·선점 정리·내 티켓·PR 상태·새 댓글·새 선점·브랜치까지 스크립트가 하고,
# 에이전트는 이 출력을 읽고 명세 검사(스킬 3단계)부터 시작한다. 큐 조작은 전부 scripts/ticket-claim.sh.
#   scripts/ticket-tick.sh                 (역할 루프는 TICKET_ROLE=architect|backend|frontend — 역할 루프는 각각 다른 체크아웃에서)
# 출력 (한 줄에 하나, 에이전트가 읽는다):
#   STATE PAUSED | OTHER-SESSION | CONTINUE | CLAIMED | WAIT | NEEDS-HUMAN | ERROR
#   ISSUE <번호> <제목>            BRANCH <이름> (이 폴더 | worktree <경로>)        WORKDIR <작업 폴더>
#   PR <번호> <OPEN|MERGED|CLOSED> checks=<pass|fail|pending|none|…> [draft]      또는  PR 없음
#   NEW_COMMENTS <n> <파일>  PR_COMMENTS <n> <파일>  SPEC <파일>  MERGE_WAIT <이유>   NEXT <에이전트가 할 일 한 줄>
# 종료코드: 0=할 일 있음(CONTINUE·CLAIMED), 1=이번 틱은 끝(PAUSED·WAIT·OTHER-SESSION·NEEDS-HUMAN), 2=오류
# 작업 폴더: 수정·스테이지된 변경이 없고 main이거나 그 티켓의 브랜치면 **이 폴더에서** 브랜치를 바꾼다 (루프 전용 체크아웃 —
#            worktree·make setup을 티켓마다 하지 않는다). 사람이 작업 중(다른 브랜치·미커밋 변경)이면 worktree를 만들고 그 안을 WORKDIR로 준다.
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
T="$HERE/ticket-claim.sh"
ROOT=$(git -C "$HERE" rev-parse --show-toplevel)
OUT="${RUN_DIR:-$ROOT/.run}/tick-${TICKET_ROLE:-all}"  # 역할 루프마다 따로 (같은 체크아웃에서 둘이 돌면 파일을 덮지 않게)
rm -rf "$OUT"; mkdir -p "$OUT"
WORK=$ROOT  # checkout_branch가 정한다

fail() { echo "STATE ERROR"; echo "NEXT $*"; exit 2; }
end()  { echo "STATE $1"; echo "NEXT $2"; exit 1; }

# ---- 브랜치 ----
slug_of() {  # 제목의 [REQ-01][BE] 같은 태그 → req-01-be (없으면 ticket)
  local s
  s=$(printf '%s' "$1" | grep -o '\[[^]]*\]' | tr -d '[]' | tr 'A-Z' 'a-z' | tr -c 'a-z0-9\n' '-' | paste -sd- - | sed 's/-\{2,\}/-/g; s/^-//; s/-$//')
  echo "${s:-ticket}"
}
cur_is_done_ticket() {  # <브랜치> 가 <type>/<번호>-… 이고 그 Issue가 닫혔으면 0 (루프가 끝낸 티켓의 브랜치 — 사람의 작업 브랜치가 아니다)
  [[ "$1" =~ ^[a-z]+/([0-9]+)- ]] || return 1
  [ "$(gh issue view "${BASH_REMATCH[1]}" --json state -q .state 2>/dev/null)" = CLOSED ]
}
checkout_branch() {  # checkout_branch <번호> <브랜치> — 이 폴더 또는 worktree. BRANCH·WORKDIR 줄을 출력하고 WORK를 정한다
  local n=$1 b=$2 cur dir remote=""
  cur=$(git -C "$ROOT" branch --show-current)
  git -C "$ROOT" fetch -q origin "$b" 2>/dev/null && remote=1  # 다른 PC·세션이 push한 브랜치
  # 미추적 파일은 브랜치를 바꿔도 그대로라 보지 않는다 (.run/ 등). 수정·스테이지된 변경이 있으면 사람이 작업 중.
  # 끝난(닫힌) 티켓의 브랜치에 남아 있는 것은 루프 자신이라 '이 폴더'로 본다
  if [ -z "$(git -C "$ROOT" status --porcelain --untracked-files=no)" ] && { [ "$cur" = main ] || [ "$cur" = "$b" ] || [[ "$cur" == */$n-* ]] || cur_is_done_ticket "$cur"; }; then
    local err
    if git -C "$ROOT" show-ref -q --verify "refs/heads/$b"; then err=$(git -C "$ROOT" switch -q "$b" 2>&1) || fail "브랜치 $b 로 바꾸지 못함: $err"
    elif [ -n "$remote" ]; then err=$(git -C "$ROOT" switch -q -c "$b" --track "origin/$b" 2>&1) || fail "origin/$b 체크아웃 실패: $err"
    else err=$(git -C "$ROOT" switch -q -c "$b" origin/main 2>&1) || fail "origin/main에서 $b 를 만들지 못함: $err"; fi
    WORK=$ROOT
    echo "BRANCH $b (이 폴더)"
  else
    dir="$(dirname "$ROOT")/$(basename "$ROOT")-wt-$n"
    if [ -d "$dir" ]; then  # 사람이 new-worktree.sh로 같은 번호의 다른 브랜치를 만들었을 수 있다
      [ "$(git -C "$dir" branch --show-current 2>/dev/null)" = "$b" ] || fail "worktree $dir 가 다른 브랜치($(git -C "$dir" branch --show-current 2>/dev/null))에 있다 — 사람이 정리"
    else
      if git -C "$ROOT" show-ref -q --verify "refs/heads/$b"; then git -C "$ROOT" worktree add -q "$dir" "$b"
      elif [ -n "$remote" ]; then git -C "$ROOT" worktree add -q --track -b "$b" "$dir" "origin/$b"
      else git -C "$ROOT" worktree add -q -b "$b" "$dir" origin/main; fi || fail "worktree 생성 실패: $dir"
      for f in frontend/.env.local backend/.env CLAUDE.local.md; do [ -f "$ROOT/$f" ] && cp "$ROOT/$f" "$dir/$f"; done
    fi
    WORK=$dir
    echo "BRANCH $b (worktree $dir — 이 폴더는 사람이 작업 중(브랜치 ${cur}·미커밋 변경). 그 안에서 make setup 후 작업, DB가 겹치면 DB_PORT=55433)"
  fi
  if [ -n "$remote" ] && ! git -C "$WORK" pull -q --ff-only origin "$b" 2>/dev/null; then  # 남이 올린 커밋이 있으면 작업 폴더에 받는다
    echo "DIVERGED origin/$b — 로컬과 갈라짐. 구현 전에 git -C $WORK merge origin/$b (충돌이면 사람에게)"
  fi
  echo "WORKDIR $WORK"
}
write_spec() {  # write_spec <번호> — 본문 + 선점 전 것까지 모든 신뢰 댓글 → SPEC 파일
  local n=$1 body
  body=$(gh issue view "$n" --json title,body -q '"# " + .title + "\n\n" + (.body // "")') || fail "#$n 명세 조회 실패 — 다음 틱에 다시"
  { echo "$body"; echo; echo "## 댓글 (신뢰 작성자, 선점 전 것까지 전부 — 나중 댓글이 이긴다)"
    "$T" comments "$n" 1970-01-01T00:00:00Z | jq -r '"- " + .user + " (" + .created_at + "): " + .body'; } >"$OUT/spec.md" || fail "#$n 댓글 조회 실패 — 다음 틱에 다시"
  echo "SPEC $OUT/spec.md"
}

# ---- 0. 킬 스위치·정리 ----
paused=$(gh issue list --label agent-pause --state open --json number --jq 'length') || fail "agent-pause 조회 실패 — gh auth status 확인"
[ "$paused" = 0 ] || end PAUSED "agent-pause 라벨이 붙은 열린 Issue가 있다 — 이번 틱은 아무것도 하지 않는다"
"$T" cleanup >/dev/null 2>&1
git -C "$ROOT" fetch -q origin main || fail "origin/main fetch 실패"
echo "TICK role=${TICKET_ROLE:-all} session=${TICKET_SESSION:-auto}"

# ---- 1. 내 진행 중 티켓 ----
mine=$("$T" mine) || fail "내 선점 목록 조회 실패"
n=$(echo "$mine" | head -1)
if [ -n "$n" ]; then
  title=$(gh issue view "$n" --json title -q .title 2>/dev/null)
  echo "ISSUE $n $title"
  "$T" owns "$n" >/dev/null 2>&1; orc=$?
  [ $orc = 1 ] && end OTHER-SESSION "#$n 은 같은 계정의 다른 세션이 작업 중 — 건드리지 않고 끝낸다 (새 티켓도 잡지 않는다)"
  [ $orc = 0 ] || fail "#$n 세션 확인 실패 (owns) — 다음 틱에 다시"
  prs=$(gh pr list --state all --limit 100 --json number,state,headRefName,body,isDraft) || fail "PR 목록 조회 실패"
  pr=$(echo "$prs" | jq -c --arg n "$n" '[.[] | select((.headRefName|test("/"+$n+"-")) or ((.body // "")|test("(?i)(closes|fixes|resolves)\\s+#"+$n+"\\b")))] | sort_by(-.number) | .[0] // empty')
  "$T" comments "$n" >"$OUT/comments.jsonl" || fail "#$n 댓글 조회 실패"
  nc=$(grep -c . "$OUT/comments.jsonl" || true)
  echo "NEW_COMMENTS $nc $OUT/comments.jsonl"
  if [ -n "$pr" ]; then
    prn=$(echo "$pr" | jq -r .number); prs_state=$(echo "$pr" | jq -r .state); prb=$(echo "$pr" | jq -r .headRefName)
    draft=$([ "$(echo "$pr" | jq -r .isDraft)" = true ] && echo " draft" || true)
    checks=$(gh pr checks "$prn" --json bucket -q '[.[].bucket] | unique | join(",")' 2>/dev/null); checks=${checks:-none}
    echo "PR $prn $prs_state checks=$checks$draft"
    "$T" pr-comments "$prn" >"$OUT/pr-comments.jsonl" 2>/dev/null || true
    npc=$(grep -c . "$OUT/pr-comments.jsonl" || true)
    echo "PR_COMMENTS $npc $OUT/pr-comments.jsonl"
    case "$prs_state" in
      MERGED)
        # 끝난 티켓 브랜치에서 main으로 (깨끗하고 그 티켓 브랜치일 때만 — 다음 선점이 이 폴더에서 바로 시작하게)
        cur=$(git -C "$ROOT" branch --show-current)
        [[ "$cur" == */$n-* ]] && [ -z "$(git -C "$ROOT" status --porcelain --untracked-files=no)" ] && git -C "$ROOT" switch -q main 2>/dev/null
        if [ "$nc" != 0 ]; then
          gh issue comment "$n" --body "<!-- ticket-agent -->
PR #$prn 은 이미 머지됐습니다 — 추가 요청은 후속 Issue로 받아야 합니다 (Issue 생성은 사람 몫)." >/dev/null 2>&1 ||
            fail "PR #$prn 은 머지됨 — 새 댓글 ${nc}건에 안내 댓글을 남기지 못함 (다음 틱에 다시)"
          end WAIT "PR #$prn 은 머지됨 — 새 댓글 ${nc}건에 '후속 Issue로' 안내 댓글을 남겼다. 코드는 더 바꾸지 않는다"
        fi
        end WAIT "PR #$prn 은 머지됨 — Issue #$n 이 닫히면 cleanup이 선점을 정리한다" ;;
      CLOSED)  # 체크아웃 불필요 — 댓글과 release만 한다
        echo "STATE CONTINUE"; echo "NEXT PR #$prn 이 머지 없이 닫혔다 — 사람이 접은 것. 이유를 묻는 댓글(마커 포함) 후 scripts/ticket-claim.sh release $n blocked. 다시 구현하지 않는다"; exit 0 ;;
      *)
        write_spec "$n"  # 세션이 바뀌어도 원 명세(본문·이전 댓글)를 같은 곳에서 읽게
        checkout_branch "$n" "$prb"
        wait_msg=$("$T" merge-wait "$n" 2>/dev/null); wrc=$?
        echo "STATE CONTINUE"
        [ $wrc = 1 ] && echo "MERGE_WAIT $(echo "$wait_msg" | paste -sd';' -)"
        case "$checks" in  # lib.sh ci_wait와 같은 기준: fail, 또는 전부 취소(통과한 체크 없음)만 실패
          *fail*|cancel) echo "NEXT PR #$prn 체크 실패·취소 — 실패한 체크(gh pr checks $prn)와 PR_COMMENTS를 읽고 같은 브랜치에서 고친 뒤 make ship (같은 체크가 3번 연속 실패하면 댓글 후 release $n blocked)" ;;
          *) if [ "$nc" != 0 ] || [ "$npc" != 0 ]; then echo "NEXT 새 댓글·리뷰 피드백을 명세 변경으로 읽어 코드·테스트에 반영하고 make ship (답할 게 있으면 마커 댓글)"
             elif [ $wrc = 1 ]; then echo "NEXT 머지 조건 대기 중 — 코드를 바꾸지 않는다. 머지 조건 Issue가 완료로 닫혔으면 make ship만 다시, 아니면 끝낸다"
             else echo "NEXT 새 댓글·실패 없음 — PR #$prn 은 리뷰·머지 대기. 할 일 없으면 끝낸다"; fi ;;
        esac
        exit 0 ;;
    esac
  fi
  echo "PR 없음"
  b=$(git -C "$ROOT" for-each-ref --format='%(refname:short)' "refs/heads/*/$n-*" | head -1)
  [ -n "$b" ] || b=$(git -C "$ROOT" ls-remote --heads origin "*/$n-*" 2>/dev/null | sed 's|.*refs/heads/||' | head -1)
  [ -n "$b" ] || b="feat/$n-$(slug_of "$title")"
  write_spec "$n"
  checkout_branch "$n" "$b"
  echo "STATE CONTINUE"; echo "NEXT 구현을 이어간다 (명세는 SPEC 파일) → make verify → ship"; exit 0
fi

# ---- 2. 새 티켓 선점 ----
cand=$("$T" list) || fail "후보 조회 실패"
cand=$(echo "$cand" | head -1)
[ -n "$cand" ] || end WAIT "후보 없음 (열린 티켓이 없거나 선행 대기·남이 선점)"
out=$("$T" claim "$cand" 2>&1); rc=$?
case $rc in
  0) ;;
  1) case "$out" in *needs-human*) echo "ISSUE $cand"; end NEEDS-HUMAN "$(echo "$out" | tail -1) — 이유를 댓글(마커 포함)로 남기고 끝낸다" ;;
                    *) end WAIT "$(echo "$out" | tail -1)" ;; esac ;;
  *) fail "선점 오류: $(echo "$out" | tail -1)" ;;
esac
title=$(gh issue view "$cand" --json title -q .title 2>/dev/null)
echo "ISSUE $cand $title"
labels=$(gh issue view "$cand" --json labels -q '[.labels[].name]|join(",")' 2>/dev/null)
case ",$labels," in *,plan,*) type=docs ;; *) type=feat ;; esac
write_spec "$cand"
checkout_branch "$cand" "$type/$cand-$(slug_of "$title")"
echo "STATE CLAIMED"
echo "NEXT 명세 검사(스킬 3단계)부터: SPEC 파일을 읽고 대상 코드가 origin/main에 있는지 본다 → 모호하면 질문 댓글 후 release $cand needs-info / 사람이 봐야 할 변경이면 release $cand needs-human / 아니면 구현(4단계)"
exit 0
