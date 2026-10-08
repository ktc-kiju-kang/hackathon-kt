#!/usr/bin/env bash
# CI와 같은 검사를 로컬에서 전부 실행한다. 하나가 실패해도 끝까지 돌리고 요약한다.
#   scripts/verify.sh            작성 중 (문서는 --draft)
#   scripts/verify.sh --strict   제출 직전 (문서 자리표시·미실행도 오류)
set -uo pipefail
. "$(dirname "$0")/lib.sh"
need_setup
strict=0; [ "${1:-}" = "--strict" ] && strict=1
mkdir -p "$RUN_DIR/verify"; rm -f "$RUN_DIR/verify/"*.log
results=()
fail=0

step() {  # step <이름> <디렉터리> <명령...>
  local name=$1 dir=$2; shift 2
  local log="$RUN_DIR/verify/$name.log" t0=$SECONDS
  printf '  %-22s ' "$name"
  if (cd "$dir" && "$@") >"$log" 2>&1; then
    printf '\033[32mPASS\033[0m (%ss)\n' $((SECONDS - t0)); results+=("PASS $name")
  else
    printf '\033[31mFAIL\033[0m (%ss) → %s\n' $((SECONDS - t0)) "${log#$ROOT/}"; results+=("FAIL $name"); fail=1
    tail -n 15 "$log" | sed 's/^/      /'
  fi
}

B="$ROOT/backend"; F="$ROOT/frontend"
ensure_db  # pytest가 PostgreSQL을 쓴다 (테스트마다 새 schema)
say "backend"
step ruff-check "$B" .venv/bin/ruff check .
step ruff-format "$B" .venv/bin/ruff format --check .
step ty "$B" .venv/bin/ty check app tests
step pytest "$B" .venv/bin/pytest -q
step e2e-lint "$ROOT" "$B/.venv/bin/ruff" check --config backend/pyproject.toml e2e
say "frontend"
step eslint "$F" npm run lint
step vitest "$F" npm test
step next-build "$F" env NEXT_DIST_DIR=.next-e2e npm run build  # make serve 중인 .next를 덮지 않게
say "문서·보안·PR 점수"
[ -f "$ROOT/scripts/test_pr_review_score.py" ] && step pr-score-test "$ROOT" python3 scripts/test_pr_review_score.py
[ -f "$ROOT/scripts/test_issue_monitor.py" ] && step issue-monitor-test "$ROOT" python3 scripts/test_issue_monitor.py
[ -f "$ROOT/scripts/test_ticket_claim.py" ] && step ticket-claim-test "$ROOT" python3 scripts/test_ticket_claim.py
if [ ! -f "$ROOT/docs/prd.md" ]; then
  printf '  %-22s \033[33mSKIP\033[0m (제출 문서 없음 — 키트 원본 레포)\n' docs
elif [ "$strict" = 1 ]; then
  step docs-strict "$ROOT" "$PY" scripts/check-docs.py
else
  step docs-draft "$ROOT" "$PY" scripts/check-docs.py --draft
fi
if command -v gitleaks >/dev/null; then
  step gitleaks "$ROOT" gitleaks git . --redact --no-banner  # 커밋 이력만 (.env·node_modules 제외)
else
  printf '  %-22s \033[33mSKIP\033[0m (gitleaks 미설치 — CI가 있으면 CI가 검사)\n' gitleaks
fi

echo
if [ "$fail" = 0 ]; then ok "검사 ${#results[@]}개 모두 통과 ($(source_version | cut -c1-12))"; else die "실패가 있습니다 — 위 로그 확인"; fi
