"""대화 저장소. 기본은 PostgreSQL(database/migrations/0001_chat.sql), 테스트는 메모리."""

import uuid
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any, Protocol

from psycopg.types.json import Jsonb

from app.agent.types import Message
from app.core.db import get_db


class ChatStore(Protocol):
    def create_conversation(self, client_id: str, title: str | None) -> dict[str, Any]: ...
    def list_conversations(self, client_id: str) -> list[dict[str, Any]]: ...
    def get_conversation(self, conversation_id: str) -> dict[str, Any] | None: ...
    def list_messages(self, conversation_id: str) -> list[dict[str, Any]]: ...
    def append_messages(self, conversation_id: str, messages: list[Message]) -> None: ...
    def set_title(self, conversation_id: str, title: str) -> None: ...


class MemoryChatStore:
    """테스트용 (tests/conftest.py). 서버 재시작 시 사라진다."""

    def __init__(self) -> None:
        self.conversations: dict[str, dict[str, Any]] = {}
        self.messages: dict[str, list[dict[str, Any]]] = {}

    def create_conversation(self, client_id: str, title: str | None) -> dict[str, Any]:
        row = {
            "id": str(uuid.uuid4()),
            "client_id": client_id,
            "title": title,
            "created_at": datetime.now(UTC),
        }
        self.conversations[row["id"]] = row
        self.messages[row["id"]] = []
        return row

    def list_conversations(self, client_id: str) -> list[dict[str, Any]]:
        rows = [c for c in self.conversations.values() if c["client_id"] == client_id]
        return sorted(rows, key=lambda c: c["created_at"], reverse=True)

    def get_conversation(self, conversation_id: str) -> dict[str, Any] | None:
        return self.conversations.get(conversation_id)

    def list_messages(self, conversation_id: str) -> list[dict[str, Any]]:
        return list(self.messages.get(conversation_id, []))

    def append_messages(self, conversation_id: str, messages: list[Message]) -> None:
        now = datetime.now(UTC)
        self.messages[conversation_id].extend(
            {"data": m.model_dump(mode="json"), "created_at": now} for m in messages
        )

    def set_title(self, conversation_id: str, title: str) -> None:
        self.conversations[conversation_id]["title"] = title


class DbChatStore:
    """PostgreSQL (database/migrations/0001_chat.sql)."""

    def create_conversation(self, client_id: str, title: str | None) -> dict[str, Any]:
        row = {
            "id": str(uuid.uuid4()),
            "client_id": client_id,
            "title": title,
            "created_at": datetime.now(UTC),
        }
        with get_db() as db:
            db.execute(
                "insert into conversations (id, client_id, title, created_at)"
                " values (%(id)s, %(client_id)s, %(title)s, %(created_at)s)",
                row,
            )
        return row

    def list_conversations(self, client_id: str) -> list[dict[str, Any]]:
        with get_db() as db:
            return db.execute(
                "select id, client_id, title, created_at from conversations"
                " where client_id = %s order by created_at desc limit 50",
                (client_id,),
            ).fetchall()

    def get_conversation(self, conversation_id: str) -> dict[str, Any] | None:
        with get_db() as db:
            return db.execute(
                "select id, client_id, title, created_at from conversations where id = %s",
                (conversation_id,),
            ).fetchone()

    def list_messages(self, conversation_id: str) -> list[dict[str, Any]]:
        with get_db() as db:  # data는 jsonb → psycopg가 dict로 돌려준다
            return db.execute(
                "select data, created_at from messages where conversation_id = %s order by id",
                (conversation_id,),
            ).fetchall()

    def append_messages(self, conversation_id: str, messages: list[Message]) -> None:
        if not messages:
            return
        now = datetime.now(UTC)
        with get_db() as db, db.cursor() as cur:
            cur.executemany(
                "insert into messages (conversation_id, data, created_at) values (%s, %s, %s)",
                [(conversation_id, Jsonb(m.model_dump(mode="json")), now) for m in messages],
            )

    def set_title(self, conversation_id: str, title: str) -> None:
        with get_db() as db:
            db.execute(
                "update conversations set title = %s where id = %s", (title, conversation_id)
            )


@lru_cache
def get_chat_store() -> ChatStore:
    return DbChatStore()
