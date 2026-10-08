"""대화 저장소. 기본은 SQLite(database/migrations/0001_chat.sql), 테스트는 메모리."""

import json
import uuid
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any, Protocol

from app.agent.types import Message
from app.core.db import get_db


class ChatStore(Protocol):
    def create_conversation(self, client_id: str, title: str | None) -> dict[str, Any]: ...
    def list_conversations(self, client_id: str) -> list[dict[str, Any]]: ...
    def get_conversation(self, conversation_id: str) -> dict[str, Any] | None: ...
    def list_messages(self, conversation_id: str) -> list[dict[str, Any]]: ...
    def append_messages(self, conversation_id: str, messages: list[Message]) -> None: ...
    def set_title(self, conversation_id: str, title: str) -> None: ...


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _dump(m: Message) -> str:
    return json.dumps(m.model_dump(mode="json"), ensure_ascii=False)


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


class SqliteChatStore:
    def create_conversation(self, client_id: str, title: str | None) -> dict[str, Any]:
        row = {
            "id": str(uuid.uuid4()),
            "client_id": client_id,
            "title": title,
            "created_at": _now(),
        }
        with get_db() as db:
            db.execute(
                "insert into conversations (id, client_id, title, created_at)"
                " values (:id, :client_id, :title, :created_at)",
                row,
            )
        return row

    def list_conversations(self, client_id: str) -> list[dict[str, Any]]:
        with get_db() as db:
            rows = db.execute(
                "select id, client_id, title, created_at from conversations"
                " where client_id = ? order by created_at desc limit 50",
                (client_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_conversation(self, conversation_id: str) -> dict[str, Any] | None:
        with get_db() as db:
            row = db.execute(
                "select id, client_id, title, created_at from conversations where id = ?",
                (conversation_id,),
            ).fetchone()
        return dict(row) if row else None

    def list_messages(self, conversation_id: str) -> list[dict[str, Any]]:
        with get_db() as db:
            rows = db.execute(
                "select data, created_at from messages where conversation_id = ? order by id",
                (conversation_id,),
            ).fetchall()
        return [{"data": json.loads(r["data"]), "created_at": r["created_at"]} for r in rows]

    def append_messages(self, conversation_id: str, messages: list[Message]) -> None:
        if not messages:
            return
        now = _now()
        with get_db() as db:
            db.executemany(
                "insert into messages (conversation_id, data, created_at) values (?, ?, ?)",
                [(conversation_id, _dump(m), now) for m in messages],
            )

    def set_title(self, conversation_id: str, title: str) -> None:
        with get_db() as db:
            db.execute("update conversations set title = ? where id = ?", (title, conversation_id))


@lru_cache
def get_chat_store() -> ChatStore:
    return SqliteChatStore()
