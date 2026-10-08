#!/usr/bin/env bash
# 개발 서버 (핫 리로드): backend :8000 + frontend :3000. Ctrl+C로 둘 다 끈다.
set -euo pipefail
. "$(dirname "$0")/lib.sh"
need_setup
for p in "$API_PORT" "$WEB_PORT"; do port_busy "$p" && die "포트 $p 사용 중 → make stop 또는 API_PORT/WEB_PORT 지정"; done

# 서버마다 프로세스 그룹을 따로 만들고(set -m) 끝날 때 그룹째 끈다 — 리로더·자식 프로세스까지 정리된다
set -m
(cd "$ROOT/backend" && exec .venv/bin/fastapi dev app/main.py --host 127.0.0.1 --port "$API_PORT" 2>&1 | sed -u 's/^/[api] /') &
api_pg=$!
(cd "$ROOT/frontend" && NEXT_PUBLIC_API_BASE_URL="http://localhost:$API_PORT" exec npm run dev -- -H 127.0.0.1 -p "$WEB_PORT" 2>&1 | sed -u 's/^/[web] /') &
web_pg=$!
cleanup() {
  trap - EXIT INT TERM
  kill -TERM -- "-$api_pg" "-$web_pg" 2>/dev/null
  sleep 2
  kill -KILL -- "-$api_pg" "-$web_pg" 2>/dev/null
  echo; ok "개발 서버 종료"
}
trap 'exit 130' INT TERM
trap cleanup EXIT
wait_http "http://localhost:$API_PORT/api/health" 60 && ok "api  http://localhost:$API_PORT/api/docs"
wait_http "http://localhost:$WEB_PORT" 120 && ok "web  http://localhost:$WEB_PORT  (Ctrl+C로 종료)"
wait
