#!/usr/bin/env bash
# 떠 있는 서버의 최소 동작 확인: health(ok·db ok·버전 일치) + 주요 화면 200.
set -euo pipefail
. "$(dirname "$0")/lib.sh"
API=${API_URL:-http://localhost:$API_PORT}; WEB=${WEB_URL:-http://localhost:$WEB_PORT}
health=$(curl -fsS "$API/api/health") || die "health 요청 실패 ($API)"
"$PY" - "$health" "${EXPECT_VERSION:-}" <<'PY' || exit 1
import json, sys
h, want = json.loads(sys.argv[1]), sys.argv[2]
bad = [k for k, ok in (("status", h["status"] == "ok"), ("db", h["db"] == "ok")) if not ok]
if want and h.get("version") != want:
    bad.append(f"version {h.get('version')} != {want}")
print(f"  health: status={h['status']} db={h['db']} llm={h['llm']} version={str(h.get('version'))[:12]}")
sys.exit(f"  ❌ {', '.join(bad)}" if bad else 0)
PY
for path in / /agent; do
  code=$(curl -s -o /dev/null -w '%{http_code}' "$WEB$path")
  [ "$code" = 200 ] || die "화면 $path → $code"
  echo "  web $path → 200"
done
ok "스모크 통과"
