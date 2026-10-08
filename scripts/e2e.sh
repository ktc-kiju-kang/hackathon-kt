#!/usr/bin/env bash
# 시험 실행 + 결과 기록 (채점 근거):
#   1) backend 단위·API 시험(pytest), frontend 단위 시험(vitest)
#   2) 격리된 로컬 배포(별도 포트·새 DB·mock LLM)에 E2E 시험(e2e/)
#   3) scripts/e2e-report.py가 TC별 결과를 docs/e2e-test.md에 반영하고 근거를 docs/evidence/<날짜>-<SHA>/에 남긴다
# 실제 LLM으로 돌리려면 E2E_LLM_PROVIDER=anthropic make e2e (비용 발생)
set -uo pipefail
. "$(dirname "$0")/lib.sh"
need_setup
VERSION=$(source_version)
OUT="$RUN_DIR/e2e"; rm -rf "$OUT"; mkdir -p "$OUT"
E2E_API_PORT=${E2E_API_PORT:-$(free_port 18000)}
E2E_WEB_PORT=${E2E_WEB_PORT:-$(free_port 13000)}
export E2E_API_PORT E2E_WEB_PORT

ensure_db

say "1/3 단위·API 시험"
(cd "$ROOT/backend" && .venv/bin/pytest -q --junitxml="$OUT/backend.xml" >"$OUT/backend.log" 2>&1); be=$?
(cd "$ROOT/frontend" && npx vitest run --reporter=default --reporter=junit --outputFile.junit="$OUT/frontend.xml" >"$OUT/frontend.log" 2>&1); fe=$?
echo "  backend pytest: $([ $be = 0 ] && echo PASS || echo FAIL)   frontend vitest: $([ $fe = 0 ] && echo PASS || echo FAIL)"

say "2/3 격리 로컬 배포 + E2E (api :$E2E_API_PORT, web :$E2E_WEB_PORT, mock LLM, 새 DB)"
cleanup() { RUN_DIR="$ROOT/.run/e2e-serve" "$ROOT/scripts/stop.sh" >/dev/null 2>&1; }
cleanup  # 지난 실행이 남긴 격리 서버부터 끈다 (pid 파일을 지우기 전에)
trap cleanup EXIT
rm -rf "$ROOT/.run/e2e-serve"
(cd "$ROOT/backend" && "$PY" -c 'from app.core import db; db.drop_schema("e2e")')  # 새 DB = 빈 e2e schema
if RUN_DIR="$ROOT/.run/e2e-serve" API_PORT=$E2E_API_PORT WEB_PORT=$E2E_WEB_PORT \
   DATABASE_SCHEMA=e2e NEXT_DIST_DIR=.next-e2e LLM_PROVIDER="${E2E_LLM_PROVIDER:-mock}" \
   "$ROOT/scripts/serve.sh" >"$OUT/serve.log" 2>&1; then
  E2E_API_URL="http://localhost:$E2E_API_PORT" E2E_WEB_URL="http://localhost:$E2E_WEB_PORT" \
  E2E_EXPECT_VERSION="$VERSION" E2E_REQUIRED=1 \
    "$PY" -m pytest "$ROOT/e2e" -q -p no:cacheprovider --junitxml="$OUT/e2e.xml" >"$OUT/e2e.log" 2>&1; ee=$?
  cp "$ROOT/.run/e2e-serve/"*.log "$OUT/" 2>/dev/null
else
  ee=1; tail -n 20 "$OUT/serve.log"; warn "로컬 배포 실패 → E2E 시험 전체 FAIL로 기록"
fi
echo "  e2e: $([ $ee = 0 ] && echo PASS || echo FAIL)"

say "3/3 결과 기록"
E2E_LLM_PROVIDER="${E2E_LLM_PROVIDER:-mock}" "$PY" "$ROOT/scripts/e2e-report.py" --version "$VERSION" \
  --results "$OUT" --exit-codes "backend=$be" "frontend=$fe" "e2e=$ee"; rep=$?
[ $be = 0 ] && [ $fe = 0 ] && [ $ee = 0 ] && [ $rep = 0 ] || die "실패한 시험이 있습니다 — 위 요약과 .run/e2e/*.log 확인"
if [ -f "$ROOT/docs/e2e-test.md" ]; then ok "시험 전부 통과 — docs/e2e-test.md·docs/evidence/ 변경을 커밋하세요 (main에서는 make record)"; else ok "시험 전부 통과"; fi
