# 공통 함수 — scripts/*.sh 에서 source 한다. macOS 기본 bash 3.2와 호환되게 쓴다.
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
RUN_DIR=${RUN_DIR:-"$ROOT/.run"}  # pid·로그 (gitignore). e2e.sh가 격리 실행에 다른 폴더를 쓴다
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
