#!/usr/bin/env bash
# 작업 브랜치를 main까지 자동으로 보낸다 — 사람은 "make ship" 한 번.
#   1 sync(main merge) + push·초안 PR(CI를 로컬 검사와 나란히 시작) → 2 make verify → 3 충돌 검사
#   → 4 시험 확인(make e2e, 기록은 되돌림) → 5 PR 본문 갱신·초안 해제 → 6 AI 리뷰(PR 본문 블록) → 7 Issue에 근거 댓글
#   → 8 CI 대기 → 머지 잠금 → main이 그새 바뀌었으면 다시 sync·verify·CI → squash 머지 → 잠금 해제
#   → 9 main 확인 (머지된 트리가 검사한 트리와 같으면 verify 생략)
# 시작 전 Issue 선점 확인(scripts/claim.sh — 남이 잡은 Issue면 멈춤), 머지 후 선점 해제.
# Issue 본문 "- 머지 조건: #N"의 Issue가 완료로 닫히지 않았으면 PR 본문에 적고 자동 머지하지 않는다 (docs/requirements-flow.md 2절).
# 환경변수: SHIP_NO_MERGE=1 (PR·리뷰까지만), SHIP_SKIP_E2E=1, SHIP_KIND=record (make record 전용), TICKET_LOOP_MERGE=1 (루프 자동 머지 — 테이블 초안 계약은 사람 머지)
set -uo pipefail
. "$(dirname "$0")/lib.sh"
need_setup
cd "$ROOT"
command -v gh >/dev/null || die "gh CLI가 필요합니다 (gh auth login)"
trap 'lock_release' EXIT
KIND=${SHIP_KIND:-work}

branch=$(git branch --show-current)
[ "$branch" != main ] || die "main에서는 ship 할 수 없습니다 — /start-task로 브랜치를 만드세요"
[[ "$branch" =~ ^(feat|fix|refactor|docs|chore|test|perf|ci)/ ]] || die "브랜치 이름은 <type>/<이슈번호>-<설명> (예: feat/12-todo-api)"
issue=""; [[ "$branch" =~ ^[a-z]+/([0-9]+)- ]] && issue=${BASH_REMATCH[1]}
[[ "$branch" =~ ^(feat|fix)/ ]] && [ -z "$issue" ] && die "feat·fix 브랜치는 이슈 번호가 필요합니다 (feat/12-...)"
[ -z "$(git status --porcelain)" ] || die "커밋 안 된 변경이 있습니다 — 커밋 후 다시 (git status)"
if [ -n "$issue" ] && [ "$KIND" != record ]; then
  "$ROOT/scripts/claim.sh" check "$issue" || exit 1
fi

say "1/9 main 반영"
before_sync=$(git rev-parse HEAD)
"$ROOT/scripts/sync.sh" || exit 1
if [ -z "${SHIP_REEXEC:-}" ] && [ -n "$(git diff --name-only "$before_sync" HEAD -- scripts Makefile)" ]; then
  warn "main에서 파이프라인 스크립트가 바뀌었습니다 → 새 버전으로 다시 실행"
  SHIP_REEXEC=1 exec "$ROOT/scripts/ship.sh"
fi
[ -n "$(git log --oneline origin/main..HEAD)" ] || die "main과 차이가 없습니다"
if [ "$KIND" = record ]; then  # 생성된 시험 기록만 담겼는지 확인 — 리뷰 없이 머지하는 유일한 경로
  extra=$(git diff --name-only origin/main...HEAD | grep -vE '^docs/(evidence/|e2e-test\.md$|prd\.md$)' || true)
  [ -z "$extra" ] || die "record 브랜치에 기록 외 파일이 있음: $extra"
fi
# CI(pull_request)는 PR이 있어야 돈다 → 지금 push하고 초안 PR을 만들어 로컬 검사·리뷰와 나란히 돌린다 (8단계 대기가 짧아진다).
# 검사가 실패하면 초안인 채 남는다 — 고친 뒤 make ship이 같은 PR을 이어 쓴다
commits=$(git log --reverse --format='- %s' origin/main..HEAD | grep -v '^- Merge ' || true)
title=$(git log --reverse --format='%s' origin/main..HEAD | grep -v '^Merge ' | head -1)
# 이미 닫힌 Issue의 후속 PR은 Refs로 잇는다 — Closes로 이으면 칸반의 "PR 연결" 자동화가
# 닫힌 카드를 In Review로 되돌리고, 다시 닫히지 않아 Done으로 돌아오지 않는다 (#109)
link=Closes
[ -n "$issue" ] && [ "$(gh issue view "$issue" --json state -q .state 2>/dev/null)" = CLOSED ] && link=Refs
out=$(git push -q -u origin "$branch" 2>&1) || { echo "$out"; die "push 실패"; }  # GitHub의 "Create a pull request" 안내는 숨긴다
pr=$(gh pr view "$branch" --json number,state -q 'select(.state=="OPEN") | .number' 2>/dev/null || true)
if [ -z "$pr" ]; then
  { [ -n "$issue" ] && printf '%s #%s\n\n' "$link" "$issue"
    printf '## 변경 내용\n%s\n\n<!-- ship:start -->\n(make ship 검사 중)\n<!-- ship:end -->\n\n<!-- ai-review:start -->\n(AI 리뷰 대기)\n<!-- ai-review:end -->\n' "$commits"
  } >"$RUN_DIR/pr-body.md"
  gh pr create --draft --base main --head "$branch" --title "$title" --body-file "$RUN_DIR/pr-body.md" >/dev/null || die "PR 생성 실패"
  pr=$(gh pr view "$branch" --json number -q .number)
  echo "  초안 PR #$pr 생성 — CI 시작"
fi

say "2/9 검사 (make verify)"
"$ROOT/scripts/verify.sh" >"$RUN_DIR/ship-verify.log" 2>&1 || { grep -E "FAIL" "$RUN_DIR/ship-verify.log"; die "verify 실패 → .run/ship-verify.log"; }
verify_line=$(grep -E "검사 [0-9]+개 모두 통과" "$RUN_DIR/ship-verify.log" | sed 's/\x1b\[[0-9;]*m//g' | tail -1)
ok "$verify_line"

say "3/9 충돌 검사"
"$ROOT/scripts/check-conflicts.sh" >"$RUN_DIR/ship-conflicts.log" 2>&1 || { cat "$RUN_DIR/ship-conflicts.log"; die "충돌 검사 ❌ — /pr-check로 해결"; }
conflict_line=$(grep "결과:" "$RUN_DIR/ship-conflicts.log" | tail -1)
grep -q "⚠️" "$RUN_DIR/ship-conflicts.log" && grep "⚠️" -A3 "$RUN_DIR/ship-conflicts.log" | sed 's/^/  /'
ok "$conflict_line"

tc_lines="- \`make e2e\`: 생략"
if [ "$KIND" != record ] && [ "${SHIP_SKIP_E2E:-}" != 1 ]; then
  say "4/9 시험 확인 (make e2e — 기록 파일은 PR에 넣지 않음)"
  "$ROOT/scripts/e2e.sh" >"$RUN_DIR/ship-e2e.log" 2>&1; e2e_rc=$?
  summary=$(ls -1d docs/evidence/*/ .run/evidence/*/ 2>/dev/null | sort -t/ -k3 | tail -n 1)  # 제출 문서 없는 레포는 .run/
  tc_lines=$( { grep -E '^- 전체:' "$summary/summary.md"; grep -E '^\| TC-' "$summary/summary.md" | cut -d'|' -f2,3 | sed 's/^/- /'; } 2>/dev/null)
  git checkout -q -- docs/e2e-test.md docs/prd.md 2>/dev/null; git clean -qfd docs/evidence 2>/dev/null
  if [ "$e2e_rc" != 0 ]; then
    echo "$tc_lines"
    grep -hE "^(FAILED|ERROR) " "$RUN_DIR"/e2e/*.log 2>/dev/null | sed 's/^/    /' | head -10
    grep -q "포트 .* 사용 중\|로컬 배포 실패" "$RUN_DIR/ship-e2e.log" && warn "격리 배포가 뜨지 않았습니다 (.run/e2e/serve.log) — 코드 문제가 아닐 수 있음"
    die "make e2e 실패 → .run/ship-e2e.log"
  fi
  ok "$(echo "$tc_lines" | head -1 | sed 's/^- //')"
fi

say "5/9 PR 본문 갱신"
head=$(git rev-parse HEAD)
ship_block="$RUN_DIR/ship-block.md"
# 역할 분담의 FE 티켓은 같은 REQ의 BE가 먼저 머지돼야 한다 — 시작 조건(선행)과 따로 "머지 조건" 줄에 둔다.
# 판정은 선행과 같은 기준(완료로 닫힘만 통과): scripts/ticket-claim.sh merge-wait (lib.sh merge_waiting·merge_gate)
waiting=""
[ -n "$issue" ] && [ "$KIND" != record ] && waiting=$(merge_waiting "$issue")
{
  echo "<!-- ship:start -->"
  echo "## 확인 (make ship 자동 기록, \`${head:0:12}\`)"
  echo "- $verify_line"
  echo "- 충돌 검사: $conflict_line"
  echo "$tc_lines"
  [ -z "$waiting" ] || echo "$waiting" | sed 's/^/- ⚠️ 머지 조건 /'
  echo "<!-- ship:end -->"
} >"$ship_block"
# 사람이 쓴 본문은 그대로 두고 <!-- ship:start/end --> 구역만 바꾼다
gh pr view "$pr" --json body -q .body >"$RUN_DIR/pr-body.old"
"$PY" scripts/pr_body.py "$RUN_DIR/pr-body.old" "$ship_block" "$issue" "$link" >"$RUN_DIR/pr-body.md"
[ "$link" = Refs ] && grep -qiE "^(closes|fixes|resolves) #$issue\b" "$RUN_DIR/pr-body.md" &&
  warn "PR 본문에 사람이 쓴 'Closes #$issue'가 있음 — Issue가 이미 닫혀 칸반 카드가 In Review로 돌아갈 수 있으니 Refs로 고치세요"
gh pr edit "$pr" --body-file "$RUN_DIR/pr-body.md" >/dev/null || die "PR 본문 갱신 실패"
if [ "$(gh pr view "$pr" --json isDraft -q .isDraft 2>/dev/null)" = true ]; then
  gh pr ready "$pr" >/dev/null 2>&1 || { [ "${SHIP_NO_MERGE:-}" = 1 ] && warn "초안 해제 실패 — gh pr ready $pr" || die "초안 해제 실패 — gh pr ready $pr 뒤 make ship"; }
fi
ok "PR #$pr 갱신 (검사 통과, 초안 해제)"

say "6/9 AI 리뷰"
if [ "$KIND" = record ]; then
  echo "  생성된 시험 기록만 담긴 PR — AI 리뷰 생략"
elif [ -n "$waiting" ] && [ "${SHIP_NO_MERGE:-}" != 1 ]; then
  # 머지까지 맡긴 실행은 어차피 머지 조건에서 멈춘다 — 리뷰는 풀린 뒤 다시 ship할 때(그때 main이 바뀌어 새로 돈다)
  echo "  머지 조건 대기 중 — AI 리뷰는 머지 조건이 풀린 뒤 make ship에서"
else
  reviewed=$(gh pr view "$pr" --json body -q .body | sed -n 's/^- 리뷰한 커밋: `\([0-9a-f]*\)`.*/\1/p' | tail -1)
  verdict=$(gh pr view "$pr" --json body -q .body | sed -n 's/^- 판정: //p' | tail -1)
  if [ -n "$reviewed" ] && [ "${head:0:12}" = "$reviewed" ] && [ -f "$RUN_DIR/ai-review.ok" ] && [ "$(cat "$RUN_DIR/ai-review.ok")" = "$head" ]; then
    echo "  같은 커밋(${reviewed})을 이미 리뷰해 통과함 — 다시 돌리지 않음 ($verdict)"
  else
    command -v claude >/dev/null || die "claude CLI가 없어 AI 리뷰를 못 합니다 — 자동 머지 중단"
    "$PY" "$ROOT/scripts/ai-review.py" --pr "$pr" --issue "$issue" --merge-wait "$waiting"; rc=$?
    [ "$rc" = 0 ] || die "AI 리뷰 결과로 자동 머지를 멈춥니다 (PR #$pr 본문의 'AI 리뷰' 확인 → 고친 뒤 make ship)"
    echo "$head" >"$RUN_DIR/ai-review.ok"
  fi
fi

if [ -n "$issue" ]; then
  say "7/9 Issue #$issue 에 근거 댓글"
  url=$(gh repo view --json url -q .url)
  gh issue comment "$issue" --body "$(printf '구현·검증 근거 (make ship)\n- PR: #%s\n- 커밋: %s/commit/%s\n- %s\n%s' "$pr" "$url" "$head" "$verify_line" "$tc_lines")" >/dev/null \
    && ok "댓글 남김" || warn "Issue 댓글 실패 (권한?) — 직접 남기세요"
fi

merge_gate "$waiting" "$pr"
schema_gate "$pr"
migration_gate "$pr"
[ "${SHIP_NO_MERGE:-}" = 1 ] && { ok "PR #$pr 준비 완료 (SHIP_NO_MERGE=1 — 머지 안 함)"; exit 0; }

say "8/9 머지 (CI → 잠금 → 최신 main 확인 → squash)"
# CI는 잠금 밖에서 기다린다 — 잠금을 잡은 채 기다리면 다른 사람의 ship이 내 CI까지 기다린다
ci_check() { ci_wait "$pr" "$(git rev-parse HEAD)"; case $? in 1) die "CI 실패 — 고친 뒤 make ship";; 2) die "CI가 끝나지 않음 — GitHub Actions 확인 후 make ship";; esac; }
for attempt in 1 2 3; do
  ci_check
  lock_acquire "PR #$pr $branch" || die "10분 동안 머지 잠금을 못 잡았습니다 — make lock-status"
  git fetch -q origin main
  git merge-base --is-ancestor origin/main HEAD && break
  lock_release  # 재반영·검사·CI는 잠금 밖에서 — 잠금을 쥔 채 20분 기다리면 남의 ship이 잠금 대기에서 실패한다
  [ "$attempt" -lt 3 ] || die "main이 계속 바뀝니다 — 잠시 뒤 make ship"
  warn "그새 main이 바뀌었습니다 → 다시 반영·검사 ($attempt/3)"
  "$ROOT/scripts/sync.sh" || die "main 반영 중 충돌 — 해결 후 make ship"
  "$ROOT/scripts/verify.sh" >"$RUN_DIR/ship-verify2.log" 2>&1 || die "main 반영 후 verify 실패 → .run/ship-verify2.log"
  git push -q origin "$branch" || die "push 실패"
done
head=$(git rev-parse HEAD)
gh pr merge "$pr" --squash --delete-branch --match-head-commit "$head" >/dev/null 2>"$RUN_DIR/ship-merge.err" \
  || { cat "$RUN_DIR/ship-merge.err"; die "머지 실패 — 보호 규칙(승인 필수 등)이면 팀원 승인 후 다시, 초안 상태면 gh pr ready $pr"; }
lock_release
ok "PR #$pr 머지"
[ -n "$issue" ] && { "$ROOT/scripts/claim.sh" done "$issue" >/dev/null 2>&1 || warn "Issue #$issue 선점 해제 실패 — scripts/claim.sh done $issue"; }

say "9/9 머지 후 main 확인"
shipped_tree=$(git rev-parse "$head^{tree}")  # 검사·CI를 통과한 트리 — squash 머지는 이 트리를 그대로 main에 올린다
# worktree에서는 main이 다른 체크아웃에 있어 switch가 안 된다 → 머지된 origin/main을 detached로 본다
git fetch -q origin main || die "origin/main fetch 실패 — 머지 후 main을 확인하지 못함"
if git switch -q main 2>/dev/null; then git pull -q --ff-only
else git switch -q --detach origin/main || die "머지된 main으로 바꾸지 못함"; echo "  (worktree는 이제 detached — 끝났으면 git worktree remove)"; fi
if [ "$(git rev-parse 'HEAD^{tree}')" = "$shipped_tree" ]; then
  ok "main 정상 ($(git rev-parse --short HEAD)) — 머지된 트리가 방금 검사한 트리와 같아 verify 생략"
elif "$ROOT/scripts/verify.sh" >"$RUN_DIR/ship-main-verify.log" 2>&1; then
  ok "main 정상 ($(git rev-parse --short HEAD))"
else
  warn "머지 후 main 검사 실패 → .run/ship-main-verify.log"
  echo "   되돌리기: git switch -c revert/$pr-main && git revert --no-edit $(git rev-parse --short HEAD) && make ship"
  exit 1
fi
if [ -n "$issue" ]; then
  echo "  Issue #$issue: $(gh issue view "$issue" --json state,stateReason -q '.state + " " + (.stateReason // "")' 2>/dev/null)"
fi
exit 0
