#!/usr/bin/env bash
# 제출 직전 확인 — 통과하면 포털에 넣을 40자 SHA를 출력한다.
#   1) 커밋 안 된 변경 없음  2) main이 origin/main과 같음(push 완료)
#   3) 검사 전부(문서 strict 포함)  4) 이 코드로 돌린 시험 근거가 있음(그 뒤 바뀐 것은 docs/만)
set -uo pipefail
. "$(dirname "$0")/lib.sh"
need_setup
cd "$ROOT"
problems=0
bad() { printf '\033[31m  ✗ %s\033[0m\n' "$*"; problems=$((problems + 1)); }
good() { printf '\033[32m  ✓ %s\033[0m\n' "$*"; }

say "1/4 작업 트리"
if [ -z "$(git status --porcelain)" ]; then good "커밋 안 된 변경 없음"; else bad "커밋 안 된 변경이 있음 (git status)"; fi

say "2/4 원격 반영"
branch=$(git branch --show-current)
git fetch -q origin 2>/dev/null || bad "origin에 접속할 수 없음 (VPN·권한 확인)"
[ "$branch" = main ] && good "main 브랜치" || bad "main이 아님 ($branch) — 제출은 main에 머지된 커밋으로"
head=$(git rev-parse HEAD)
remote=$(git rev-parse -q --verify origin/main 2>/dev/null || echo none)
[ "$head" = "$remote" ] && good "origin/main과 같음" || bad "HEAD($head)가 origin/main($remote)과 다름 — pull 또는 push"

say "3/4 검사 (문서 strict)"
if "$ROOT/scripts/verify.sh" --strict >"$RUN_DIR/submit-verify.log" 2>&1; then good "verify --strict 통과"
else bad "verify --strict 실패 → .run/submit-verify.log"; grep -E "FAIL|오류" "$RUN_DIR/submit-verify.log" | head -20 | sed 's/^/      /'; fi

say "4/4 시험 근거"
latest=$(ls -1d docs/evidence/*/ 2>/dev/null | grep -v -- '-dirty/$' | sort | tail -n 1)
if [ -z "$latest" ]; then
  bad "docs/evidence/에 커밋된 코드로 돌린 시험 근거가 없음 → make e2e 후 커밋"
else
  ev_sha=$(sed -n 's/^- 소스 SHA: `\([0-9a-f]\{40\}\)`.*/\1/p' "$latest/summary.md")
  if [ -z "$ev_sha" ]; then bad "$latest/summary.md에서 SHA를 못 읽음"
  elif ! git cat-file -e "$ev_sha^{commit}" 2>/dev/null; then bad "근거의 SHA ${ev_sha}가 이 레포에 없음"
  elif git diff --quiet "$ev_sha" HEAD -- "${CODE_PATHSPEC[@]}"; then
    good "최신 근거 $(basename "$latest") — 그 뒤 코드 변경 없음 (문서만 변경)"
  else
    bad "근거(${ev_sha}) 이후 코드가 바뀜 → make e2e 다시 실행 후 커밋"
    git diff --stat "$ev_sha" HEAD -- "${CODE_PATHSPEC[@]}" | tail -n 5 | sed 's/^/      /'
  fi
  if ! grep -q '^- 전체: PASS' "$latest/summary.md"; then
    bad "최신 근거가 전체 PASS가 아님 — 실패·미실행 묶음이 있음 (${latest}summary.md)"
  fi
fi

echo
if [ "$problems" = 0 ]; then
  ok "제출 준비 완료. 포털 '본선 제출'에 아래 SHA를 입력하세요:"
  echo
  echo "    $head"
  echo
  echo "   확인: GitHub에서 이 커밋이 보이는지 → 포털에 SHA 저장 → '소스 제출 완료'"
else
  die "문제 ${problems}개 — 고친 뒤 다시 make submit-check"
fi
