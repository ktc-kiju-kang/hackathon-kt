#!/usr/bin/env bash
# 보안 공통 점검 — 비밀값(gitleaks)·의존성 취약점(frontend 운영 의존성 npm audit, backend pip-audit).
#   make audit   → 결과 .run/audit/, docs/security-compliance.md 4절 "공통 점검" 두 행에 결과·시각·SHA를 적는다 (문서가 있을 때).
# 종료코드: 0=발견 없음(도구가 없어 미실행인 항목 포함), 1=비밀값·high 이상 취약점 발견, 2=실행 오류
set -uo pipefail
. "$(dirname "$0")/lib.sh"
cd "$ROOT"
A="$RUN_DIR/audit"; mkdir -p "$A"; rm -f "$A"/*.json "$A"/*.log "$A"/*.err  # 이전 실행 보고서가 이번 결과로 읽히지 않게
fail=0; err=0
# 제출 레포(security-compliance.md 있음)에서는 보고서를 docs/audit/<시각>-<SHA>/에 복사해 그 경로를 적는다 — .run/은 gitignore라 제출본에서 못 연다.
# docs/evidence/ 아래에 두지 않는다: 그 폴더는 e2e 실행 폴더만 있어야 한다 (submit-check·ship이 "최신 폴더"를 e2e 근거로 집고, ship이 커밋 전 것을 지운다)
ev=""; [ -f docs/security-compliance.md ] && ev="docs/audit/$(TZ=Asia/Seoul date +%Y%m%d-%H%M%S)-$(git rev-parse --short HEAD)"
where=${ev:-.run/audit}

say "1/3 비밀값 (gitleaks)"
if command -v gitleaks >/dev/null; then
  if gitleaks detect --source . --no-banner --redact --report-format json --report-path "$A/gitleaks.json" >"$A/gitleaks.log" 2>&1; then
    secrets="PASS — gitleaks detect 발견 0건"; ok "비밀값 없음"
  elif [ -s "$A/gitleaks.json" ]; then
    n=$(python3 -c 'import json,sys; print(len(json.load(open(sys.argv[1]))))' "$A/gitleaks.json" 2>/dev/null || echo "?")
    secrets="FAIL — gitleaks ${n}건 ($where/gitleaks.json)"; warn "비밀값 의심 ${n}건 → $where/gitleaks.json"; fail=1
  else
    secrets="오류 — gitleaks 실행 실패 ($where/gitleaks.log)"; warn "gitleaks 실행 실패 → $where/gitleaks.log"; err=1
  fi
else
  secrets="미실행 — gitleaks 미설치 (brew install gitleaks; CI Security 워크플로가 대신 검사)"; warn "gitleaks 미설치 — brew install gitleaks"
fi

say "2/3 frontend 운영 의존성 (npm audit --omit=dev)"
(cd frontend && npm audit --omit=dev --json >"$A/npm-audit.json" 2>"$A/npm-audit.err") || true
counts=$(python3 - "$A/npm-audit.json" <<'PY'
import json, sys
try:
    d = json.load(open(sys.argv[1]))
    v = d["metadata"]["vulnerabilities"]
    print(v.get("high", 0), v.get("critical", 0), v.get("total", 0))
except Exception:
    print("? ? ?")
PY
)
read -r high crit total <<<"${counts:-? ? ?}"
if [ "$high" = "?" ]; then npm_res="오류 — npm audit 실행 실패 ($where/npm-audit.err)"; warn "npm audit 실행 실패 → $where/npm-audit.err"; err=1
elif [ $((high + crit)) -gt 0 ]; then npm_res="FAIL — high ${high}·critical $crit (전체 $total, $where/npm-audit.json)"; warn "frontend 운영 의존성 취약점 high ${high}·critical $crit → npm audit (frontend)"; fail=1
else npm_res="PASS — high·critical 0 (전체 $total)"; ok "frontend 운영 의존성 high·critical 없음 (전체 $total)"; fi

say "3/3 backend 의존성 (pip-audit)"
PYA="$ROOT/backend/.venv/bin/python"
req=$(ls backend/requirements.txt 2>/dev/null | head -1)
if [ ! -x "$PYA" ] || [ -z "$req" ]; then pip_res="미실행 — backend/.venv 또는 requirements.txt 없음 (make setup)"; warn "backend 가상환경이 없어 pip-audit 생략"
else
  # requirements-dev.txt에 넣는 것은 의존성 단독 PR(chore/deps-pip-audit)이라 즉석 설치하되 판은 고정한다
  "$PYA" -m pip_audit --version >/dev/null 2>&1 || "$PYA" -m pip install -q "pip-audit==${PIP_AUDIT_VERSION:-2.10.1}" >"$A/pip-audit-install.log" 2>&1 || true
  if ! "$PYA" -m pip_audit --version >/dev/null 2>&1; then pip_res="미실행 — pip-audit 설치 실패 ($where/pip-audit-install.log)"; warn "pip-audit 설치 실패 (네트워크?)"
  else
    "$PYA" -m pip_audit -r "$req" --progress-spinner off -f json -o "$A/pip-audit.json" >"$A/pip-audit.log" 2>&1; rc=$?
    n=$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(sum(len(x.get("vulns",[])) for x in d.get("dependencies",[])))' "$A/pip-audit.json" 2>/dev/null || echo "?")
    if [ $rc = 0 ]; then pip_res="PASS — 발견 0건"; ok "backend 의존성 취약점 없음"
    elif [ "$n" != "?" ] && [ $rc = 1 ]; then pip_res="FAIL — ${n}건 ($where/pip-audit.json)"; warn "backend 의존성 취약점 ${n}건 → $where/pip-audit.json"; fail=1
    else pip_res="오류 — pip-audit 실행 실패 ($where/pip-audit.log)"; warn "pip-audit 실행 실패 → $where/pip-audit.log"; err=1; fi
  fi
fi

if [ -n "$ev" ]; then mkdir -p "$ev" && cp "$A"/*.json "$A"/*.log "$A"/*.err "$ev"/ 2>/dev/null; echo "  보고서 → $ev/ (커밋해서 근거로)"; fi
stamp="$(TZ=Asia/Seoul date '+%Y-%m-%d %H:%M') KST, $(git rev-parse --short HEAD)"
python3 "$ROOT/scripts/audit_doc.py" --secrets "$secrets" --deps "npm audit(운영) $npm_res · pip-audit $pip_res" --stamp "$stamp"
echo
echo "  비밀값: $secrets"
echo "  의존성: npm audit(운영) $npm_res · pip-audit $pip_res"
[ $fail = 0 ] || { echo "  ❌ 발견된 항목을 고치거나(의존성 변경은 chore/deps-<이름> 단독 PR) security-compliance.md에 예외 이유를 적으세요"; exit 1; }
[ $err = 0 ] || exit 2
exit 0
