#!/usr/bin/env bash
# 배포 스모크 테스트. 배포 파이프라인과 /deploy-status 에서 사용.
# 사용법: scripts/smoke.sh [기대 커밋 SHA]
set -uo pipefail
API_URL=${API_URL:-https://hackathon-kt-api.onrender.com}
WEB_URL=${WEB_URL:-https://hackathon-kt.vercel.app}
expect_sha=${1:-}
fail=0
ok() { echo "✅ $*"; }
ng() { echo "❌ $*"; fail=1; }

body=$(curl -fsS -m 90 "$API_URL/api/health") && echo "$body" | grep -q '"status":"ok"' \
  && ok "API health: $body" || ng "API health 실패: ${body:-no response}"
if [ -n "$expect_sha" ]; then
  echo "$body" | grep -q "\"version\":\"$expect_sha\"" && ok "API version = $expect_sha" || ng "API version 불일치 (기대 $expect_sha)"
fi

code=$(curl -s -o /dev/null -w "%{http_code}" -m 30 "$WEB_URL") && [ "$code" = 200 ] \
  && ok "Web $WEB_URL → 200" || ng "Web $WEB_URL → $code"

curl -s -i -m 30 -H "Origin: $WEB_URL" "$API_URL/api/health" | grep -qi "access-control-allow-origin: $WEB_URL" \
  && ok "CORS $WEB_URL 허용" || ng "CORS $WEB_URL 차단됨"

exit $fail
