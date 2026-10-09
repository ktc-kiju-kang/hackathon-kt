# 공통 함수 — scripts/*.sh 에서 source 한다. macOS 기본 bash 3.2와 호환되게 쓴다.
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
RUN_DIR=${RUN_DIR:-"$ROOT/.run"}  # pid·로그 (gitignore). e2e.sh가 격리 실행에 다른 폴더를 쓴다
mkdir -p "$RUN_DIR"
API_PORT=${API_PORT:-8000}
WEB_PORT=${WEB_PORT:-3000}
PY="$ROOT/backend/.venv/bin/python"

say()  { printf '\033[1m▶ %s\033[0m\n' "$*"; }
ok()   { printf '\033[32m✅ %s\033[0m\n' "$*"; }
warn() { printf '\033[33m⚠️  %s\033[0m\n' "$*"; }
die()  { printf '\033[31m❌ %s\033[0m\n' "$*" >&2; exit 1; }

need_setup() {
  [ -x "$PY" ] || die "backend 가상환경이 없습니다 → make setup"
  [ -d "$ROOT/frontend/node_modules" ] || die "frontend 의존성이 없습니다 → make setup"
}

# 시험 근거가 보는 "코드" = docs/·*.md 밖의 모든 추적 파일 (submit-check.sh와 같은 규칙)
CODE_PATHSPEC=(. ':(exclude)docs' ':(exclude)*.md')

# 실행 중인 소스 버전: 커밋 SHA, 커밋 안 된 코드 변경이 있으면 -dirty (문서만 바뀐 것은 제외)
source_version() {
  local sha
  sha=$(git -C "$ROOT" rev-parse HEAD 2>/dev/null) || { echo "unknown"; return; }
  if [ -n "$(git -C "$ROOT" status --porcelain --untracked-files=no -- "${CODE_PATHSPEC[@]}" 2>/dev/null)" ]; then
    echo "${sha}-dirty"
  else
    echo "$sha"
  fi
}

port_busy() { lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1; }

# ensure_db — PostgreSQL에 접속되면 그대로, 아니면 docker compose로 db만 띄운다.
#   CI는 services: postgres로 이미 떠 있다. 접속 주소는 backend 설정(DATABASE_URL, 기본 localhost:55432)
db_ok() { (cd "$ROOT/backend" && "$PY" -c 'import psycopg; from app.core.config import settings
psycopg.connect(settings.database_url, connect_timeout=2).close()') >/dev/null 2>&1; }
ensure_db() {
  db_ok && return 0
  command -v docker >/dev/null && docker info >/dev/null 2>&1 \
    || die "PostgreSQL에 접속할 수 없고 Docker도 꺼져 있습니다 → Docker Desktop 실행 후 make db"
  say "PostgreSQL 기동 (docker compose db)"
  docker compose -f "$ROOT/compose.yaml" up -d --wait --quiet-pull db >"$RUN_DIR/db-up.log" 2>&1 \
    || { tail -n 20 "$RUN_DIR/db-up.log"; die "db 기동 실패 → .run/db-up.log (포트 55432를 다른 PostgreSQL이 쓰면 DB_PORT·DATABASE_URL 지정)"; }
  db_ok || die "db는 떴지만 접속 실패 — DATABASE_URL 확인 (backend/.env)"
}

# free_port <시작> — 시작 번호부터 비어 있는 포트 (worktree 두 개에서 동시에 e2e를 돌려도 안 부딪히게)
free_port() {
  local p=$1
  while port_busy "$p" && [ "$p" -lt $(( $1 + 50 )) ]; do p=$((p + 1)); done
  echo "$p"
}

# wait_http <url> <초> — 200이 올 때까지 기다린다
wait_http() {
  local url=$1 secs=${2:-60} i=0
  while [ "$i" -lt "$secs" ]; do
    curl -fsS -o /dev/null "$url" 2>/dev/null && return 0
    sleep 1; i=$((i + 1))
  done
  return 1
}

# start_bg <이름> <로그> <명령...> — 백그라운드 실행, pid 기록
start_bg() {
  local name=$1 log=$2; shift 2
  mkdir -p "$RUN_DIR"
  # set -m: 자기 프로세스 그룹(pgid = pid)으로 띄워, stop_bg가 자식까지 그룹째 끈다
  (set -m; nohup "$@" >"$log" 2>&1 & echo $! >"$RUN_DIR/$name.pid")
}

# stop_bg <이름> — pid 파일의 프로세스 그룹(자식 포함)을 끈다
stop_bg() {
  local f="$RUN_DIR/$1.pid" pid
  [ -f "$f" ] || return 0
  pid=$(cat "$f")
  if kill -0 "$pid" 2>/dev/null; then
    kill -TERM -- "-$pid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null || true
    for _ in 1 2 3 4 5; do kill -0 "$pid" 2>/dev/null || break; sleep 1; done
    kill -KILL -- "-$pid" 2>/dev/null || kill -KILL "$pid" 2>/dev/null || true
  fi
  rm -f "$f"
}

# ---- 머지 잠금 (세 사람이 동시에 머지하지 않게) -------------------------------------
# GitHub에 refs/heads/merge-lock 브랜치를 "없을 때만" 만든다 (--force-with-lease=ref: 는 원자적 생성).
# 잠금 커밋 메시지에 누가·언제를 남긴다. 15분 넘은 잠금은 주인이 죽은 것으로 보고 가져온다.
LOCK_REF=refs/heads/merge-lock
LOCK_STALE_SEC=${LOCK_STALE_SEC:-900}

lock_info() {  # 현재 잠금: "<sha> <epoch> <누가>" 또는 빈 값
  local sha
  sha=$(git -C "$ROOT" ls-remote origin "$LOCK_REF" 2>/dev/null | cut -f1)
  [ -n "$sha" ] || return 0
  git -C "$ROOT" fetch -q origin "$LOCK_REF" 2>/dev/null || true
  echo "$sha $(git -C "$ROOT" log -1 --format='%ct %s' "$sha" 2>/dev/null)"
}

lock_acquire() {  # lock_acquire <설명> — 잡을 때까지 기다린다 (최대 10분)
  local what=$1 tree commit info age waited=0
  tree=$(git -C "$ROOT" hash-object -t tree /dev/null)
  while :; do
    commit=$(git -C "$ROOT" commit-tree "$tree" -m "$(git config user.name): $what" </dev/null)
    if git -C "$ROOT" push -q --force-with-lease="$LOCK_REF:" origin "$commit:$LOCK_REF" 2>/dev/null; then
      LOCK_SHA=$commit
      return 0
    fi
    info=$(lock_info)
    if [ -n "$info" ]; then
      age=$(( $(date +%s) - $(echo "$info" | cut -d' ' -f2) ))
      if [ "$age" -gt "$LOCK_STALE_SEC" ]; then
        warn "${age}초 지난 잠금을 가져옵니다: $(echo "$info" | cut -d' ' -f3-)"
        git -C "$ROOT" push -q --force-with-lease="$LOCK_REF:$(echo "$info" | cut -d' ' -f1)" origin ":$LOCK_REF" 2>/dev/null || true
        continue
      fi
      [ $((waited % 30)) -eq 0 ] && echo "  머지 대기 중 — $(echo "$info" | cut -d' ' -f3-) (${age}초째)"
    fi
    [ "$waited" -ge 600 ] && return 1
    sleep 5; waited=$((waited + 5))
  done
}

lock_release() {  # 내 잠금일 때만 지운다
  [ -n "${LOCK_SHA:-}" ] || return 0
  git -C "$ROOT" push -q --force-with-lease="$LOCK_REF:$LOCK_SHA" origin ":$LOCK_REF" 2>/dev/null || true
  LOCK_SHA=
}

# 머지 조건 (Issue 본문 "- 머지 조건: #N", docs/requirements-flow.md 2절) — make ship이 쓴다
merge_waiting() {  # merge_waiting <Issue> — 머지하면 안 되는 이유를 한 줄씩 (빈 값 = 머지 가능). 판정 실패도 이유다
  local out rc err="$RUN_DIR/merge-wait.err"  # 이유(stdout)만 PR 본문에, 진단(stderr)은 판정 실패 때만
  out=$("$ROOT/scripts/ticket-claim.sh" merge-wait "$1" 2>"$err"); rc=$?
  case $rc in
    0) sed 's/^/  머지 조건 /' "$err" >&2 ;;  # 풀린 조건(예: "#11 완료로 닫힘 ✅")은 화면에만
    1) echo "$out" ;;
    *) echo "판정 실패: $(tail -1 "$err" 2>/dev/null | grep . || echo "종료코드 $rc") — 다시 make ship" ;;
  esac
}

merge_gate() {  # merge_gate <이유> <PR> — 이유가 있으면 SHIP_NO_MERGE=1은 경고만, 머지까지 맡긴 실행은 멈춘다
  [ -n "$1" ] || return 0
  echo "$1" | sed 's/^/  머지 조건 /'
  [ "${SHIP_NO_MERGE:-}" = 1 ] || die "머지 조건이 풀리지 않아 머지하지 않습니다 — 풀린 뒤 다시 make ship (PR #$2 은 그대로 둠)"
  warn "머지 조건이 풀리지 않음 — PR 본문에 적었습니다. 풀린 뒤에 머지하세요"
}

# 스키마 게이트 (G3) — 루프 자동 머지(TICKET_LOOP_MERGE=1)에서 테이블 SQL 초안이 있는 계약을 바꾼 PR은 사람이 머지한다.
# BE 루프가 그 초안으로 마이그레이션을 만들기 때문. 사람이 직접 ship하면 그 사람이 확인한 것으로 본다
schema_contracts() {  # origin/main...HEAD에서 바뀐 계약 중 바뀌기 전이나 후에 '## 테이블' 절이 있는 것 (공백 구분)
  local f out=""
  for f in $(git -C "$ROOT" diff --name-only origin/main...HEAD -- 'docs/contracts/*.md' ':!docs/contracts/README.md'); do
    { git -C "$ROOT" show "HEAD:$f"; git -C "$ROOT" show "origin/main:$f"; } 2>/dev/null | grep -q '^## 테이블' && out="$out $f"
  done
  echo "${out# }"
}

schema_gate() {  # schema_gate <PR> — 해당 계약이 있으면 SHIP_NO_MERGE=1은 경고, 루프 자동 머지는 멈춘다
  local found
  [ "${TICKET_LOOP_MERGE:-}" = 1 ] && [ "${SHIP_KIND:-}" != record ] || return 0  # 기록 PR은 계약을 못 바꾼다
  found=$(schema_contracts)
  [ -n "$found" ] || return 0
  [ "${SHIP_NO_MERGE:-}" = 1 ] || die "테이블 SQL 초안이 있는 계약이 바뀜 ($found) — 사람이 스키마를 확인하고 GitHub에서 머지합니다 (G3, PR #$1)"
  warn "테이블 SQL 초안이 있는 계약이 바뀜 ($found) — 스키마를 확인하고 머지하세요 (G3)"
}

migration_gate() {  # migration_gate <PR> — 루프 자동 머지에서 새 마이그레이션이 계약 초안과 다르면 사람이 머지한다
  local out rc
  [ "${TICKET_LOOP_MERGE:-}" = 1 ] && [ "${SHIP_KIND:-}" != record ] || return 0
  out=$(python3 "$ROOT/scripts/migration_draft.py" 2>&1); rc=$?
  [ $rc = 0 ] && return 0
  echo "$out" | sed 's/^/  마이그레이션 /'
  [ "${SHIP_NO_MERGE:-}" = 1 ] || die "마이그레이션이 계약의 테이블 SQL 초안과 다름 — 사람이 확인하고 GitHub에서 머지합니다 (PR #$1)"
  warn "마이그레이션이 계약의 테이블 SQL 초안과 다름 — 확인하고 머지하세요"
}

# ---- ship 보조 -------------------------------------------------------------------------
ci_wait() {  # ci_wait <PR> — PR 체크가 끝날 때까지 기다린다 (최대 20분). 0=통과(CI 없음 포함), 1=실패, 2=시간 초과
  local pr=$1 checks states i
  checks=$(gh pr checks "$pr" --json name,bucket -q 'length' 2>/dev/null || echo 0)
  [ "${checks:-0}" -gt 0 ] 2>/dev/null || { echo "  이 레포에 CI가 없어 로컬 verify 결과로 진행"; return 0; }
  echo "  CI 대기 (최대 20분)…"
  for i in $(seq 1 "${CI_WAIT_MAX:-120}"); do
    states=$(gh pr checks "$pr" --json bucket -q '[.[].bucket] | unique | join(",")' 2>/dev/null)
    # cancel은 새 실행으로 대체된 것(PR 본문 수정 → PR Review 재실행)이라 실패로 보지 않는다
    case "$states" in *fail*) gh pr checks "$pr" 2>/dev/null | grep -i "fail"; return 1;; esac
    case "$states" in *pending*) sleep "${CI_POLL_SEC:-10}";; *) ok "CI 통과 ($states)"; return 0;; esac
  done
  return 2
}

scripts_tests_needed() {  # 키트 스크립트 자체 시험(scripts/test_*.py)을 돌릴지 — CI·키트 원본 레포·scripts/가 바뀐 브랜치에서만
  [ -n "${CI:-}" ] && return 0
  [ -f "$ROOT/templates/starter/export.py" ] && return 0
  [ -n "$(git -C "$ROOT" status --porcelain -- scripts Makefile 2>/dev/null)" ] && return 0
  local changed
  changed=$(git -C "$ROOT" diff --name-only origin/main...HEAD -- scripts Makefile 2>/dev/null) || return 0  # origin/main이 없으면 돌린다
  [ -n "$changed" ]
}
