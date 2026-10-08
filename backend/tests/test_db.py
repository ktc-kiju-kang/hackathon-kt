import psycopg
import pytest

from app.agent.types import Message
from app.core import db
from app.services.chat_store import DbChatStore


def test_migrations_apply_once():
    with db.get_db() as conn:
        versions = [r["version"] for r in conn.execute("select version from schema_migrations")]
    assert versions == sorted(f.stem for f in db.MIGRATIONS_DIR.glob("*.sql"))
    db.reset_for_tests()
    db.init_db()  # 두 번째 적용은 아무것도 하지 않는다 (같은 테이블을 다시 만들면 예외)
    with db.get_db() as conn:
        assert len(conn.execute("select version from schema_migrations").fetchall()) == len(
            versions
        )


def test_rollback_on_error():
    sql = "insert into conversations (id, client_id, created_at) values ('a', 'c', now())"
    with pytest.raises(psycopg.errors.UniqueViolation), db.get_db() as conn:
        conn.execute(sql)
        conn.execute(sql)  # 같은 id → UniqueViolation → 첫 insert까지 rollback
    with db.get_db() as conn:
        assert conn.execute("select count(*) as n from conversations").fetchone() == {"n": 0}


def test_tests_use_isolated_schema():
    """테스트 데이터가 앱 schema(public)에 섞이지 않는다."""
    with db.get_db() as conn:
        row = conn.execute("select current_schema() as s").fetchone()
    assert row is not None and row["s"].startswith("test_")


def test_db_chat_store_roundtrip():
    store = DbChatStore()
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


def test_db_chat_store_strips_nul():
    """PostgreSQL은 NUL을 저장하지 못한다 — 500 대신 지우고 저장한다."""
    store = DbChatStore()
    conv = store.create_conversation("client-a", "a\x00b")
    store.append_messages(conv["id"], [Message(role="user", content="안\x00녕")])
    store.set_title(conv["id"], "제\x00목")
    saved = store.get_conversation(conv["id"])
    assert saved is not None and saved["title"] == "제목"
    [msg] = store.list_messages(conv["id"])
    assert Message.model_validate(msg["data"]).content == "안녕"
