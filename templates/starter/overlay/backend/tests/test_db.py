import sqlite3

import pytest

from app.agent.types import Message
from app.core import db
from app.services.chat_store import SqliteChatStore


def test_migrations_apply_once():
    with db.get_db() as conn:
        versions = [r[0] for r in conn.execute("select version from schema_migrations")]
    assert versions == sorted(f.stem for f in db.MIGRATIONS_DIR.glob("*.sql"))
    db.reset_for_tests()
    db.init_db()  # 두 번째 적용은 아무것도 하지 않는다 (같은 테이블을 다시 만들면 예외)
    with db.get_db() as conn:
        assert len(list(conn.execute("select version from schema_migrations"))) == len(versions)


def test_rollback_on_error():
    with pytest.raises(sqlite3.IntegrityError), db.get_db() as conn:
        sql = "insert into conversations (id, client_id, created_at) values ('a', 'c', ?)"
        conn.execute(sql, ("t1",))
        conn.execute(sql, ("t2",))  # 같은 id → IntegrityError → 첫 insert까지 rollback
    with db.get_db() as conn:
        assert conn.execute("select count(*) from conversations").fetchone()[0] == 0


def test_sqlite_chat_store_roundtrip():
    store = SqliteChatStore()
    conv = store.create_conversation("client-a", None)
    store.append_messages(conv["id"], [Message(role="user", content="안녕")])
    store.set_title(conv["id"], "제목")

    saved = store.get_conversation(conv["id"])
    assert saved is not None and saved["title"] == "제목"
    assert [c["id"] for c in store.list_conversations("client-a")] == [conv["id"]]
    assert store.list_conversations("client-b") == []  # 다른 소유자에게는 보이지 않는다
    [msg] = store.list_messages(conv["id"])
    assert Message.model_validate(msg["data"]).content == "안녕"
    assert store.get_conversation("missing") is None
