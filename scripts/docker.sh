#!/usr/bin/env bash
# docker compose로 로컬 실행 — make dev / make serve / make stop / make status 가 부른다.
#   dev   : 소스 마운트 + 핫 리로드, 포그라운드 (Ctrl+C로 종료)
#   up    : 프로덕션 빌드로 백그라운드 + 스모크 (make serve)
#   down  : 끈다 (DB 파일 backend/data/app.db는 남는다)
#   status: 컨테이너·health
# 시험(make e2e)·검사(make verify)·ship은 docker를 쓰지 않는다 — CI와 같은 네이티브 도구로 돈다.
set -euo pipefail
. "$(dirname "$0")/lib.sh"
cd "$ROOT"
need_docker() {
  command -v docker >/dev/null || die "docker가 없습니다 → Docker Desktop 설치 (또는 NATIVE=1 make dev)"
  docker info >/dev/null 2>&1 || die "Docker가 꺼져 있습니다 → Docker Desktop 실행 (또는 NATIVE=1)"
}
have_docker() { command -v docker >/dev/null && docker info >/dev/null 2>&1; }
export API_PORT WEB_PORT
dc() { docker compose "$@"; }
dcdev() { docker compose -f compose.yaml -f compose.dev.yaml "$@"; }
running() { [ -n "$(dc ps -q 2>/dev/null)" ]; }
check_ports() {
  running && die "이미 docker로 떠 있습니다 → make stop"
  for p in "$API_PORT" "$WEB_PORT"; do port_busy "$p" && die "포트 $p 사용 중 → make stop (또는 API_PORT/WEB_PORT 지정)"; done
  return 0
}
mkdir -p backend/data
[ -f backend/.env ] || { cp backend/.env.example backend/.env; ok "backend/.env 생성 (키가 없으면 mock LLM)"; }

case "${1:-}" in
  dev)
    need_docker; check_ports
    trap 'exit 130' INT TERM
    trap 'trap - EXIT INT TERM; dcdev down >/dev/null 2>&1; echo; ok "개발 서버 종료"' EXIT
    APP_VERSION=$(source_version) dcdev up --build --remove-orphans &
    up_pid=$!
    wait_http "http://localhost:$API_PORT/api/health" 300 && ok "api  http://localhost:$API_PORT/api/docs"
    wait_http "http://localhost:$WEB_PORT" 300 && ok "web  http://localhost:$WEB_PORT  (Ctrl+C로 종료)"
    wait "$up_pid"
    ;;
  up)
    need_docker; check_ports
    VERSION=$(source_version)
    [ "${VERSION%-dirty}" != "$VERSION" ] && warn "커밋하지 않은 변경이 있습니다 — 이 실행 결과는 제출 근거가 되지 않습니다 ($VERSION)"
    say "docker 빌드·기동 (api :$API_PORT, web :$WEB_PORT)"
    APP_VERSION=$VERSION dc up -d --build --wait --remove-orphans >"$RUN_DIR/docker-up.log" 2>&1 \
      || { tail -n 30 "$RUN_DIR/docker-up.log"; dc logs --tail 30; dc down >/dev/null 2>&1; die "docker 기동 실패 → .run/docker-up.log"; }
    wait_http "http://localhost:$WEB_PORT" 60 || { dc logs --tail 30 web; dc down >/dev/null 2>&1; die "web이 뜨지 않음"; }
    say "스모크 확인"
    EXPECT_VERSION="$VERSION" "$ROOT/scripts/smoke.sh" || { dc down >/dev/null 2>&1; die "스모크 실패 — 서버를 내렸습니다"; }
    printf '%s\n' "$VERSION" >"$RUN_DIR/serve.version"
    ok "로컬 배포 완료 (docker, $VERSION)"
    echo "   web  http://localhost:$WEB_PORT"
    echo "   api  http://localhost:$API_PORT/api/docs"
    echo "   로그 docker compose logs -f   종료: make stop"
    ;;
  down)
    have_docker && running || exit 0
    dcdev down --remove-orphans >/dev/null 2>&1 || true
    rm -f "$RUN_DIR/serve.version"
    ok "docker 종료 (DB는 backend/data/app.db에 남음)"
    ;;
  status)
    have_docker && running || { echo "  docker: 꺼짐"; exit 0; }
    dc ps --format '  {{.Service}}: {{.State}} {{.Status}}'
    ;;
  *) die "사용: scripts/docker.sh dev|up|down|status";;
esac
