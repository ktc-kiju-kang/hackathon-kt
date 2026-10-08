#!/usr/bin/env bash
# 로컬 배포 상태: 프로세스·포트·health.
set -uo pipefail
. "$(dirname "$0")/lib.sh"
for n in backend frontend; do
  f="$RUN_DIR/$n.pid"
  if [ -f "$f" ] && kill -0 "$(cat "$f")" 2>/dev/null; then echo "  $n: 실행 중 (pid $(cat "$f"))"; else echo "  $n: 꺼짐"; fi
done
curl -fsS "http://localhost:$API_PORT/api/health" 2>/dev/null && echo || echo "  health: 응답 없음 (:$API_PORT)"
[ -f "$RUN_DIR/serve.version" ] && echo "  배포 버전: $(cat "$RUN_DIR/serve.version")"
echo "  현재 소스: $(source_version)"
