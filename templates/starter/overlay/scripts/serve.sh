#!/usr/bin/env bash
# 로컬 배포: 프로덕션 빌드로 backend(:8000)·frontend(:3000)를 백그라운드로 띄우고 스모크 확인까지 한다.
#   make serve / make stop / make status
#   API_PORT·WEB_PORT·DATABASE_PATH·LLM_PROVIDER 환경변수로 바꿀 수 있다 (e2e.sh가 격리 실행에 쓴다).
#   이 PC에서만 열린다(127.0.0.1) — 행사장 네트워크의 다른 사람이 붙어 LLM 비용을 쓰지 못하게.
set -euo pipefail
. "$(dirname "$0")/lib.sh"
need_setup
for p in "$API_PORT" "$WEB_PORT"; do port_busy "$p" && die "포트 $p 사용 중 → make stop (또는 API_PORT/WEB_PORT 지정)"; done
mkdir -p "$RUN_DIR"
VERSION=$(source_version)
export NEXT_DIST_DIR=${NEXT_DIST_DIR:-.next}
API="http://localhost:$API_PORT"; WEB="http://localhost:$WEB_PORT"
[ "${VERSION%-dirty}" != "$VERSION" ] && warn "커밋하지 않은 변경이 있습니다 — 이 실행 결과는 제출 근거가 되지 않습니다 ($VERSION)"

say "frontend 프로덕션 빌드 (API=$API)"
(cd "$ROOT/frontend" && NEXT_PUBLIC_API_BASE_URL="$API" npm run build >"$RUN_DIR/build.log" 2>&1) \
  || { tail -n 30 "$RUN_DIR/build.log"; die "빌드 실패 → .run/build.log"; }

say "backend 기동"
export APP_VERSION="$VERSION" CORS_ORIGINS="$WEB"
(cd "$ROOT/backend" && start_bg backend "$RUN_DIR/backend.log" .venv/bin/fastapi run app/main.py --host 127.0.0.1 --port "$API_PORT")
wait_http "$API/api/health" 30 || { tail -n 30 "$RUN_DIR/backend.log"; "$ROOT/scripts/stop.sh" >/dev/null; die "backend가 뜨지 않음 → .run/backend.log"; }

say "frontend 기동"
(cd "$ROOT/frontend" && start_bg frontend "$RUN_DIR/frontend.log" ./node_modules/.bin/next start -H 127.0.0.1 -p "$WEB_PORT")
wait_http "$WEB" 60 || { tail -n 30 "$RUN_DIR/frontend.log"; "$ROOT/scripts/stop.sh" >/dev/null; die "frontend가 뜨지 않음 → .run/frontend.log"; }

say "스모크 확인"
API_URL="$API" WEB_URL="$WEB" EXPECT_VERSION="$VERSION" "$ROOT/scripts/smoke.sh" \
  || { "$ROOT/scripts/stop.sh" >/dev/null; die "스모크 실패 — 서버를 내렸습니다"; }
printf '%s\n' "$VERSION" >"$RUN_DIR/serve.version"
ok "로컬 배포 완료 ($VERSION)"
echo "   web  $WEB"
echo "   api  $API/api/docs"
echo "   로그 .run/backend.log · .run/frontend.log   종료: make stop"
