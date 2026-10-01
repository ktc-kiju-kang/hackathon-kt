#!/usr/bin/env bash
# database/migrations/*.sql 중 아직 적용 안 된 것만 순서대로 적용한다.
# 적용 기록은 public.schema_migrations 테이블. 파일 하나 = 트랜잭션 하나.
# 사용법: DATABASE_URL=postgres://... scripts/migrate.sh [--dry-run]
set -euo pipefail
: "${DATABASE_URL:?DATABASE_URL 환경변수가 필요합니다}"
dry_run=${1:-}
dir="$(cd "$(dirname "$0")/.." && pwd)/database/migrations"
export PGOPTIONS="${PGOPTIONS:-} -c client_min_messages=warning"
psql_() { psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -X -q "$@"; }

psql_ -c "create table if not exists public.schema_migrations (
  version text primary key,
  applied_at timestamptz not null default now()
); alter table public.schema_migrations enable row level security;"

applied=$(psql_ -At -c "select version from public.schema_migrations")
pending=0
for f in $(ls "$dir"/*.sql 2>/dev/null | sort); do
  v=$(basename "$f" .sql)
  grep -qx "$v" <<<"$applied" && continue
  pending=$((pending + 1))
  if [ "$dry_run" = "--dry-run" ]; then
    echo "pending: $v"
    continue
  fi
  echo "applying: $v"
  psql_ --single-transaction -f "$f" -c "insert into public.schema_migrations(version) values ('$v')"
done
if [ "$pending" -eq 0 ]; then echo "up to date"
elif [ "$dry_run" = "--dry-run" ]; then echo "$pending pending"
else echo "applied: $pending"; fi
