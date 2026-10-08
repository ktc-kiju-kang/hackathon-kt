"""SQLite 연결과 마이그레이션. 서비스 레이어(app/services/*)에서만 사용한다.

예:
    with get_db() as db:
        rows = db.execute("select * from items where owner = ?", (owner,)).fetchall()

- DB 파일: `settings.database_path` (기본 backend/data/app.db, gitignore). 외부 서비스 없음.
- 마이그레이션: `database/migrations/NNNN_<설명>.sql`을 번호순으로 한 번씩, 첫 연결 때 적용한다
  (`schema_migrations`에 기록). 이미 적용된 파일은 고치지 말고 새 번호로 추가한다.
"""

import re
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from app.core.config import settings

MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "database" / "migrations"
_NAME = re.compile(r"\d{4}_[a-z0-9_]+")
_lock = threading.Lock()
_ready: set[str] = set()


def _connect() -> sqlite3.Connection:
    path = settings.database_path
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # row["컬럼"]으로 읽는다
    conn.execute("pragma foreign_keys = on")
    return conn


def init_db() -> None:
    """아직 적용하지 않은 마이그레이션을 적용한다. 파일 하나 = 트랜잭션 하나."""
    path = settings.database_path
    if path in _ready:
        return
    with _lock:
        if path in _ready:
            return
        conn = _connect()
        try:
            conn.execute(
                "create table if not exists schema_migrations"
                " (version text primary key, applied_at text not null default (datetime('now')))"
            )
            done = {r[0] for r in conn.execute("select version from schema_migrations")}
            for f in sorted(MIGRATIONS_DIR.glob("*.sql")):
                if f.stem in done:
                    continue
                if not _NAME.fullmatch(f.stem):
                    raise RuntimeError(f"마이그레이션 파일 이름은 NNNN_<설명>.sql: {f.name}")
                sql = f.read_text(encoding="utf-8")
                conn.executescript(
                    f"begin;\n{sql}\n"
                    f"insert into schema_migrations (version) values ('{f.stem}');\ncommit;"
                )
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        _ready.add(path)


@contextmanager
def get_db() -> Iterator[sqlite3.Connection]:
    """요청 하나의 연결. 블록이 정상 종료하면 commit, 예외면 rollback."""
    init_db()
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def reset_for_tests() -> None:
    """테스트가 DB 경로를 바꿀 때 마이그레이션 적용 기록(메모리)을 비운다."""
    _ready.clear()
