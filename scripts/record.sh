#!/usr/bin/env bash
# 시험 기록 커밋 — main 최신 코드로 make e2e → docs/e2e-test.md·prd.md·evidence + AI 활용 기록(development.md 3절) + README '결과 한눈에'·compliance 요약 숫자만 담은 PR을 자동 머지.
# 기록 파일은 이 경로로만 main에 들어간다 (기능 PR끼리 같은 표를 고쳐 충돌하지 않게).
# 한 사람(기록 담당)이 2~3시간마다, 그리고 제출 전에 실행한다.
set -uo pipefail
. "$(dirname "$0")/lib.sh"
need_setup
cd "$ROOT"
[ -z "$(git status --porcelain)" ] || die "커밋 안 된 변경이 있습니다"
git switch -q main || die "main으로 전환 실패"
"$ROOT/scripts/sync.sh" || exit 1
say "main $(git rev-parse --short HEAD) 시험"
"$ROOT/scripts/e2e.sh"; rc=$?
python3 "$ROOT/scripts/dev_log.py" || warn "AI 활용 기록(development.md) 갱신 실패 — 시험 기록은 그대로 진행"
python3 "$ROOT/scripts/readme_summary.py" || warn "README '결과 한눈에' 갱신 실패 — 시험 기록은 그대로 진행"
[ -n "$(git status --porcelain docs)" ] || die "기록할 변경이 없습니다"
verdict=$( [ "$rc" = 0 ] && echo PASS || echo FAIL )
[ "$rc" = 0 ] || warn "실패가 있지만 그대로 기록합니다 (정직한 근거). 고친 뒤 다시 make record"
b="docs/record-$(date +%Y%m%d-%H%M%S)"
git switch -q -c "$b"
git add docs/e2e-test.md docs/prd.md docs/evidence
[ -f docs/development.md ] && git add docs/development.md
git add README.md docs/security-compliance.md 2>/dev/null || true  # 결과 요약 숫자 (readme_summary.py)
git commit -q -m "docs(e2e): 시험 기록 $(git rev-parse --short main) (전체 $verdict)"
SHIP_KIND=record "$ROOT/scripts/ship.sh"
