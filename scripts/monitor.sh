#!/usr/bin/env bash
# Issue 모니터 + 로컬 대시보드를 백그라운드로 켜고 끈다. 본체는 scripts/issue-monitor.py.
#   scripts/monitor.sh start [옵션…]   켠다 (이미 켜져 있으면 안내만). 옵션은 issue-monitor.py 로 그대로 전달 (예: --quiet-start --no-slack)
#   scripts/monitor.sh stop            끈다
#   scripts/monitor.sh status          켜져 있는지 + 대시보드 주소 + 마지막 확인 시각
#   scripts/monitor.sh open            대시보드를 브라우저로 연다
#   scripts/monitor.sh logs            최근 로그
# 환경변수: MONITOR_PORT(기본 8765)  MONITOR_NO_OPEN=1(start 때 브라우저 열지 않음)
# Slack webhook 은 SLACK_WEBHOOK_URL 또는 ~/.config/hackathon-kt/slack-webhook — 시크릿이라 이 스크립트도 출력하지 않는다.
set -uo pipefail
ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || { echo "❌ 저장소 안에서 실행하세요" >&2; exit 1; }
RUN="${XDG_CACHE_HOME:-$HOME/.cache}/hackathon-kt"; mkdir -p "$RUN"
PID_FILE="$RUN/issue-monitor.pid"; LOG="$RUN/issue-monitor.log"
PORT=${MONITOR_PORT:-8765}; URL="http://127.0.0.1:$PORT"

running() { [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; }
open_url() { command -v open >/dev/null && open "$URL" || command -v xdg-open >/dev/null && xdg-open "$URL" || echo "브라우저에서 $URL 을 여세요"; }

case "${1:-status}" in
  start)
    shift || true
    if running; then echo "이미 켜져 있음 (pid $(cat "$PID_FILE")) → $URL"; exit 0; fi
    cd "$ROOT" || exit 1
    nohup python3 scripts/issue-monitor.py --serve --port "$PORT" "$@" >>"$LOG" 2>&1 &
    echo $! >"$PID_FILE"
    for _ in $(seq 1 20); do
      curl -fsS "$URL/api/state" >/dev/null 2>&1 && break
      kill -0 "$(cat "$PID_FILE")" 2>/dev/null || { echo "❌ 시작 실패 — 로그:" >&2; tail -n 15 "$LOG" >&2; rm -f "$PID_FILE"; exit 1; }
      sleep 0.5
    done
    echo "✅ 모니터 시작 (pid $(cat "$PID_FILE")) → $URL"
    [ "${MONITOR_NO_OPEN:-}" = 1 ] || open_url ;;
  stop)
    if running; then kill "$(cat "$PID_FILE")" && echo "🛑 모니터 중지"; else echo "켜져 있지 않음"; fi
    rm -f "$PID_FILE" ;;
  status)
    if running; then
      echo "켜져 있음 (pid $(cat "$PID_FILE")) → $URL"
      curl -fsS "$URL/api/state" 2>/dev/null | python3 -c 'import json,sys; d=json.load(sys.stdin); print("  마지막 확인:", d["polled_at"], "· 연속 실패:", d["fails"], "· Slack:", d["slack"], "· 이슈", len(d["issues"]), "· PR", len(d["prs"]))' 2>/dev/null || echo "  (대시보드 응답 없음)"
    else echo "꺼져 있음 — 켜기: scripts/monitor.sh start"; fi ;;
  open) open_url ;;
  logs) tail -n "${2:-30}" "$LOG" 2>/dev/null || echo "로그 없음" ;;
  *) sed -n '2,9p' "$0"; exit 2 ;;
esac
