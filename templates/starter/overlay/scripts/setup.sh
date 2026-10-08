#!/usr/bin/env bash
# 개발 환경 준비: 버전 확인 → backend 가상환경·의존성 → frontend 의존성 → .env 파일. 여러 번 실행해도 된다.
set -euo pipefail
. "$(dirname "$0")/lib.sh"

say "도구 버전 확인"
command -v node >/dev/null || die "Node.js 20+ 가 필요합니다"
node_major=$(node -p 'process.versions.node.split(".")[0]')
[ "$node_major" -ge 20 ] || die "Node.js 20+ 가 필요합니다 (현재 $(node -v))"
PYTHON=${PYTHON:-python3}
"$PYTHON" -c 'import sys; sys.exit(sys.version_info < (3, 11))' \
  || die "Python 3.11+ 가 필요합니다 (PYTHON=python3.12 make setup 처럼 지정 가능)"
ok "node $(node -v), $("$PYTHON" --version)"

say "backend 의존성"
cd "$ROOT/backend"
[ -x .venv/bin/python ] || "$PYTHON" -m venv .venv
.venv/bin/pip install -q --disable-pip-version-check -r requirements-dev.txt
[ -f .env ] || { cp .env.example .env; ok "backend/.env 생성 (키가 없으면 mock LLM)"; }

say "frontend 의존성"
cd "$ROOT/frontend"
if [ -f package-lock.json ]; then npm ci --no-audit --no-fund --loglevel=error; else npm install --no-audit --no-fund; fi
[ -f .env.local ] || { cp .env.example .env.local; ok "frontend/.env.local 생성"; }

ok "준비 완료 → make dev (개발) / make verify (검사) / make serve (로컬 배포)"
