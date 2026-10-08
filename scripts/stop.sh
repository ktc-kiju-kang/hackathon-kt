#!/usr/bin/env bash
# make serve 로 띄운 서버를 끈다.
set -uo pipefail
. "$(dirname "$0")/lib.sh"
stop_bg frontend; stop_bg backend
rm -f "$RUN_DIR/serve.version"
ok "로컬 배포 종료"
