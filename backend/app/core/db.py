"""PostgreSQL 연결과 마이그레이션. 서비스 레이어(app/services/*)에서만 사용한다.

예:
    with get_db() as db:
        rows = db.execute("select * from items where owner = %s", (owner,)).fetchall()

- 접속: `settings.database_url` (기본: 각자 PC의 docker compose `db`, `make db`로 띄운다).
  행은 dict(`row["컬럼"]`). 값은 반드시 `%s`/`%(이름)s` 자리표시자로 넘긴다 (이어 붙이지 않는다).
- schema: `settings.database_schema` (기본 public). 테스트는 테스트마다 새 schema, e2e는 `e2e`.
- 마이그레이션: `database/migrations/YYYYMMDDHHMM_<설명>.sql`을 이름순으로 한 번씩 적용한다
  (서버 시작 시, `schema_migrations`에 기록). 적용된 파일은 고치지 말고 새 파일로 추가한다.
"""

import re
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from app.core.config import settings

MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "database" / "migrations"
# NNNN_설명(키트 기본) 또는 YYYYMMDDHHMM_설명(새 파일 — 세 사람이 동시에 만들어도 번호가 안 겹친다)
_NAME = re.compile(r"(\d{4}|\d{12})_[a-z0-9_]+")
_MIGRATION_LOCK = 7_310_001  # pg_advisory_xact_lock 키 — 서버 여러 개가 동시에 떠도 한 번만 적용
_lock = threading.Lock()
_ready: set[tuple[str, str]] = set()

Connection = psycopg.Connection[dict[str, Any]]


def _connect() -> Connection:
    # schema 이름은 config에서 [a-z0-9_]만 허용한다 (search_path에 그대로 들어간다)
    # Connection[...]을 명시해야 타입 검사기(ty)가 dict 행으로 본다 (psycopg.connect 오버로드 한계)
    return Connection.connect(
        settings.database_url,
        row_factory=dict_row,
        connect_timeout=5,
        options=f"-c search_path={settings.database_schema}",
    )


def init_db() -> None:
    """아직 적용하지 않은 마이그레이션을 적용한다. 파일 하나 = 트랜잭션 하나."""
    key = (settings.database_url, settings.database_schema)
    if key in _ready:
        return
    with _lock:
        if key in _ready:
            return
        with _connect() as conn:
            with conn.transaction():
                # 서버 둘이 동시에 처음 뜰 때 create ... if not exists끼리도 부딪힐 수 있다
                conn.execute("select pg_advisory_xact_lock(%s)", (_MIGRATION_LOCK,))
                conn.execute(
                    sql.SQL("create schema if not exists {}").format(
                        sql.Identifier(settings.database_schema)
                    )
                )
                conn.execute(
                    "create table if not exists schema_migrations"
                    " (version text primary key, applied_at timestamptz not null default now())"
                )
            for f in sorted(MIGRATIONS_DIR.glob("*.sql")):
                if not _NAME.fullmatch(f.stem):
                    raise RuntimeError(
                        f"마이그레이션 파일 이름은 YYYYMMDDHHMM_<설명>.sql: {f.name}"
                    )
                with conn.transaction():
                    conn.execute("select pg_advisory_xact_lock(%s)", (_MIGRATION_LOCK,))
                    done = conn.execute(
                        "select 1 from schema_migrations where version = %s", (f.stem,)
                    ).fetchone()
                    if done:
                        continue
                    # 레포에 커밋된 마이그레이션 파일 = 신뢰된 SQL (사용자 입력이 아님)
                    conn.execute(f.read_text(encoding="utf-8"))  # ty: ignore[no-matching-overload]
                    conn.execute("insert into schema_migrations (version) values (%s)", (f.stem,))
        _ready.add(key)


@contextmanager
def get_db() -> Iterator[Connection]:
    """요청 하나의 연결. 블록이 정상 종료하면 commit, 예외면 rollback."""
    init_db()
    with _connect() as conn:  # psycopg: 정상 종료 → commit, 예외 → rollback, 그리고 close
        yield conn


def reset_for_tests() -> None:
    """테스트가 DB·schema를 바꿀 때 마이그레이션 적용 기록(메모리)을 비운다."""
    _ready.clear()


def drop_schema(schema: str) -> None:
    """테스트·e2e 격리용 schema를 지운다 (public은 지우지 않는다)."""
    if schema == "public" or not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", schema):
        raise ValueError(f"지울 수 없는 schema: {schema!r}")
    with psycopg.connect(settings.database_url, connect_timeout=5, autocommit=True) as conn:
        conn.execute(sql.SQL("drop schema if exists {} cascade").format(sql.Identifier(schema)))
