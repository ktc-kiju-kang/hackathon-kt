#!/usr/bin/env bash
# docker compose로 로컬 실행 — make dev / make serve / make stop / make status 가 부른다.
#   dev   : 소스 마운트 + 핫 리로드, 포그라운드 (Ctrl+C로 종료)
#   up    : 프로덕션 빌드로 백그라운드 + 스모크 (make serve)
#   down  : 끈다 (db 포함. 데이터는 docker volume pgdata에 남는다)
#   db    : PostgreSQL만 띄운다 (NATIVE=1 실행·pytest용 — make verify·e2e는 알아서 띄운다)
#   reset : DB 데이터 전부 삭제 (volume 삭제)
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
GIT_REMOTE_URL=$(git -C "$ROOT" remote get-url origin 2>/dev/null | sed -E 's#://[^@/]+@#://#' || true)  # 주소 속 자격 증명은 뺀다
export GIT_REMOTE_URL
dc() { docker compose "$@"; }
dcdev() { docker compose -f compose.yaml -f compose.dev.yaml "$@"; }
running() { [ -n "$(dc ps -q api web 2>/dev/null)" ]; }  # db만 떠 있는 것(make db·verify)은 실행 중 아님
check_ports() {
  running && die "이미 docker로 떠 있습니다 → make stop"
  for p in "$API_PORT" "$WEB_PORT"; do port_busy "$p" && die "포트 $p 사용 중 → make stop (또는 API_PORT/WEB_PORT 지정)"; done
  # db 포트: 이 폴더의 db가 이미 떠 있으면 괜찮다 (make db·verify). 다른 worktree·프로그램이면 막는다
  if [ -z "$(dc ps -q db 2>/dev/null)" ] && port_busy "${DB_PORT:-55432}"; then
    die "포트 ${DB_PORT:-55432}(db) 사용 중 — 다른 worktree면 DB_PORT=55433 + backend/.env의 DATABASE_URL도 같은 포트로"
  fi
  return 0
}
prepare() {  # dev·up 전용 — stop·status는 파일을 만들지 않는다
  need_docker; check_ports
  [ -x "$PY" ] || die "먼저 make setup (스모크·검사에 로컬 도구가 필요합니다)"
  mkdir -p backend/data .run/evidence  # 마운트할 폴더 (없으면 docker가 root 소유로 만든다)
  [ -f backend/.env ] || { cp backend/.env.example backend/.env; ok "backend/.env 생성 (키가 없으면 mock LLM)"; }
}
# wait_up <url> <초> <pid> — 200이 오거나, compose가 먼저 죽으면(빌드 실패 등) 바로 실패
wait_up() {
  local i=0
  while [ "$i" -lt "$2" ]; do
    curl -fsS -o /dev/null "$1" 2>/dev/null && return 0
    kill -0 "$3" 2>/dev/null || return 1
    sleep 1; i=$((i + 1))
  done
  return 1
}

case "${1:-}" in
  dev)
    prepare
    trap 'exit 130' INT TERM
    trap 'trap - EXIT INT TERM; dcdev down >/dev/null 2>&1; echo; ok "개발 서버 종료"' EXIT
    APP_VERSION=$(source_version) dcdev up --build --remove-orphans &
    up_pid=$!
    wait_up "http://localhost:$API_PORT/api/health" 300 "$up_pid" || die "api가 뜨지 않음 (위 docker 로그 확인)"
    ok "api  http://localhost:$API_PORT/api/docs"
    wait_up "http://localhost:$WEB_PORT" 300 "$up_pid" || die "web이 뜨지 않음 (위 docker 로그 확인)"
    ok "web  http://localhost:$WEB_PORT  (Ctrl+C로 종료)"
    wait "$up_pid"
    ;;
  up)
    prepare
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
    have_docker && [ -n "$(dc ps -q 2>/dev/null)" ] || exit 0
    dcdev down --remove-orphans >/dev/null 2>&1 || true
    rm -f "$RUN_DIR/serve.version"
    ok "docker 종료 (DB 데이터는 volume pgdata에 남음 — 지우려면 make db-reset)"
    ;;
  db)
    need_docker
    dc up -d --wait --quiet-pull db >"$RUN_DIR/db-up.log" 2>&1 \
      || { tail -n 5 "$RUN_DIR/db-up.log"; die "db 기동 실패 (포트 ${DB_PORT:-55432} 사용 중이면 DB_PORT·DATABASE_URL 지정)"; }
    ok "PostgreSQL 127.0.0.1:${DB_PORT:-55432} (app/app, db app)"
    ;;
  reset)
    need_docker
    dcdev down -v --remove-orphans >/dev/null 2>&1 || true
    rm -f "$RUN_DIR/serve.version"
    ok "DB 데이터 삭제 (서버도 내림) — 다음 실행 때 마이그레이션이 처음부터 적용된다"
    ;;
  status)
    have_docker && [ -n "$(dc ps -q 2>/dev/null)" ] || { echo "  docker: 꺼짐"; exit 0; }
    dc ps --format '  {{.Service}}: {{.State}} {{.Status}}'
    ;;
  *) die "사용: scripts/docker.sh dev|up|down|db|reset|status";;
esac
