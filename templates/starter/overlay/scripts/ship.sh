#!/usr/bin/env bash
# 작업 브랜치를 main까지 자동으로 보낸다 — 사람은 "make ship" 한 번.
#   1 sync(main merge) → 2 make verify → 3 충돌 검사 → 4 시험 확인(make e2e, 기록은 되돌림)
#   → 5 push·PR 생성/갱신 → 6 AI 리뷰(PR 본문 블록) → 7 Issue에 근거 댓글
#   → 8 머지 잠금 → main이 그새 바뀌었으면 다시 sync·verify → CI 대기 → squash 머지 → 잠금 해제
#   → 9 main에서 make verify (머지 후 깨졌는지)
# 환경변수: SHIP_NO_MERGE=1 (PR·리뷰까지만), SHIP_SKIP_E2E=1, SHIP_KIND=record (make record 전용)
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
  summary=$(ls -1d docs/evidence/*/ 2>/dev/null | sort | tail -n 1)
  tc_lines=$( { grep -E '^- 전체:' "$summary/summary.md"; grep -E '^\| TC-' "$summary/summary.md" | cut -d'|' -f2,3 | sed 's/^/- /'; } 2>/dev/null)
  git checkout -q -- docs/e2e-test.md docs/prd.md 2>/dev/null; git clean -qfd docs/evidence 2>/dev/null
  [ "$e2e_rc" = 0 ] || { echo "$tc_lines"; die "make e2e 실패 → .run/ship-e2e.log"; }
  ok "$(echo "$tc_lines" | head -1 | sed 's/^- //')"
fi

say "5/9 push·PR"
git push -q -u origin "$branch" || die "push 실패"
head=$(git rev-parse HEAD)
pr=$(gh pr view "$branch" --json number,state -q 'select(.state=="OPEN") | .number' 2>/dev/null || true)
commits=$(git log --reverse --format='- %s' origin/main..HEAD | grep -v '^- Merge ' || true)
title=$(git log --reverse --format='%s' origin/main..HEAD | grep -v '^Merge ' | head -1)
ship_block="$RUN_DIR/ship-block.md"
{
  echo "<!-- ship:start -->"
  echo "## 확인 (make ship 자동 기록, \`${head:0:12}\`)"
  echo "- $verify_line"
  echo "- 충돌 검사: $conflict_line"
  echo "$tc_lines"
  echo "<!-- ship:end -->"
} >"$ship_block"
if [ -z "$pr" ]; then
  { [ -n "$issue" ] && printf 'Closes #%s\n\n' "$issue"
    printf '## 변경 내용\n%s\n\n' "$commits"
    cat "$ship_block"
    printf '\n<!-- ai-review:start -->\n(AI 리뷰 대기)\n<!-- ai-review:end -->\n'
  } >"$RUN_DIR/pr-body.md"
  gh pr create --base main --head "$branch" --title "$title" --body-file "$RUN_DIR/pr-body.md" >/dev/null || die "PR 생성 실패"
  pr=$(gh pr view "$branch" --json number -q .number)
  ok "PR #$pr 생성"
else
  # 사람이 쓴 본문은 그대로 두고 <!-- ship:start/end --> 구역만 바꾼다
  gh pr view "$pr" --json body -q .body >"$RUN_DIR/pr-body.old"
  "$PY" - "$RUN_DIR/pr-body.old" "$ship_block" "$issue" >"$RUN_DIR/pr-body.md" <<'PY'
import re, sys
body, block, issue = open(sys.argv[1]).read(), open(sys.argv[2]).read().strip(), sys.argv[3]
pat = re.compile(r"<!-- ship:start -->.*?<!-- ship:end -->", re.S)
body = pat.sub(lambda _: block, body) if pat.search(body) else body.rstrip() + "\n\n" + block
if issue and not re.search(rf"(?im)^(closes|fixes|resolves) #{issue}\b", body):
    body = f"Closes #{issue}\n\n" + body
print(body)
PY
  gh pr edit "$pr" --body-file "$RUN_DIR/pr-body.md" >/dev/null || die "PR 본문 갱신 실패"
  ok "PR #$pr 갱신"
fi

say "6/9 AI 리뷰"
if [ "$KIND" = record ]; then
  echo "  생성된 시험 기록만 담긴 PR — AI 리뷰 생략"
else
  command -v claude >/dev/null || die "claude CLI가 없어 AI 리뷰를 못 합니다 — 자동 머지 중단"
  "$PY" "$ROOT/scripts/ai-review.py" --pr "$pr" --issue "$issue"; rc=$?
  [ "$rc" = 0 ] || die "AI 리뷰 결과로 자동 머지를 멈춥니다 (PR #$pr 본문의 'AI 리뷰' 확인 → 고친 뒤 make ship)"
fi

if [ -n "$issue" ]; then
  say "7/9 Issue #$issue 에 근거 댓글"
  url=$(gh repo view --json url -q .url)
  gh issue comment "$issue" --body "$(printf '구현·검증 근거 (make ship)\n- PR: #%s\n- 커밋: %s/commit/%s\n- %s\n%s' "$pr" "$url" "$head" "$verify_line" "$tc_lines")" >/dev/null \
    && ok "댓글 남김" || warn "Issue 댓글 실패 (권한?) — 직접 남기세요"
fi

[ "${SHIP_NO_MERGE:-}" = 1 ] && { ok "PR #$pr 준비 완료 (SHIP_NO_MERGE=1 — 머지 안 함)"; exit 0; }

say "8/9 머지 (잠금 → 최신 main 확인 → CI → squash)"
lock_acquire "PR #$pr $branch" || die "10분 동안 머지 잠금을 못 잡았습니다 — make lock-status"
git fetch -q origin main
if ! git merge-base --is-ancestor origin/main HEAD; then
  warn "그새 main이 바뀌었습니다 → 다시 반영·검사"
  "$ROOT/scripts/sync.sh" || die "main 반영 중 충돌 — 해결 후 make ship"
  "$ROOT/scripts/verify.sh" >"$RUN_DIR/ship-verify2.log" 2>&1 || die "main 반영 후 verify 실패 → .run/ship-verify2.log"
  git push -q origin "$branch" || die "push 실패"
fi
head=$(git rev-parse HEAD)
checks=$(gh pr checks "$pr" --json name,bucket -q 'length' 2>/dev/null || echo 0)
if [ "${checks:-0}" -gt 0 ]; then
  echo "  CI 대기 (최대 20분)…"
  for _ in $(seq 1 120); do
    states=$(gh pr checks "$pr" --json bucket -q '[.[].bucket] | unique | join(",")' 2>/dev/null)
    case "$states" in *fail*|*cancel*) gh pr checks "$pr" | grep -iE "fail|cancel"; die "CI 실패 — 고친 뒤 make ship";; esac
    case "$states" in *pending*) sleep 10;; *) break;; esac
  done
  case "$states" in *pending*) die "CI가 20분 안에 끝나지 않음";; esac
  ok "CI 통과 ($states)"
else
  echo "  이 레포에 CI가 없어 로컬 verify 결과로 진행"
fi
gh pr merge "$pr" --squash --delete-branch --match-head-commit "$head" >/dev/null 2>"$RUN_DIR/ship-merge.err" \
  || { cat "$RUN_DIR/ship-merge.err"; die "머지 실패 — 보호 규칙(승인 필수 등)이면 팀원 승인 후 다시"; }
lock_release
ok "PR #$pr 머지"

say "9/9 머지 후 main 확인"
git switch -q main && git pull -q --ff-only
if "$ROOT/scripts/verify.sh" >"$RUN_DIR/ship-main-verify.log" 2>&1; then
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
