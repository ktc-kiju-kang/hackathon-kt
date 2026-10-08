#!/usr/bin/env bash
# 머지 잠금 상태. 오래된 잠금(주인이 중단됨)은 15분이 지나면 다음 make ship이 가져간다.
set -uo pipefail
. "$(dirname "$0")/lib.sh"
info=$(lock_info)
if [ -z "$info" ]; then ok "머지 잠금 없음"; exit 0; fi
age=$(( $(date +%s) - $(echo "$info" | cut -d' ' -f2) ))
echo "  잠금: $(echo "$info" | cut -d' ' -f3-) — ${age}초 전"
[ "${1:-}" = --break ] && { git -C "$ROOT" push -q --force-with-lease="$LOCK_REF:$(echo "$info" | cut -d' ' -f1)" origin ":$LOCK_REF" && ok "잠금 해제"; }
echo "  강제 해제(주인이 확실히 멈췄을 때만): scripts/lock-status.sh --break"
