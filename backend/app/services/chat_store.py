"""대화 저장소. Supabase 설정이 있으면 DB(database/migrations/0002_chat.sql), 없으면 메모리.

메모리 저장소는 로컬·CI용이다 (서버 재시작 시 사라짐).
"""

import uuid
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any, Protocol

from app.agent.types import Message
from app.config import settings


class ChatStore(Protocol):
    def create_conversation(self, client_id: str, title: str | None) -> dict[str, Any]: ...
    def list_conversations(self, client_id: str) -> list[dict[str, Any]]: ...
    def get_conversation(self, conversation_id: str) -> dict[str, Any] | None: ...
    def list_messages(self, conversation_id: str) -> list[dict[str, Any]]: ...
    def append_messages(self, conversation_id: str, messages: list[Message]) -> None: ...
    def set_title(self, conversation_id: str, title: str) -> None: ...


class MemoryChatStore:
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


class SupabaseChatStore:
    def __init__(self) -> None:
        from app.db import get_supabase

        self.db = get_supabase()

    def create_conversation(self, client_id: str, title: str | None) -> dict[str, Any]:
        res = (
            self.db.table("conversations")
            .insert({"client_id": client_id, "title": title})
            .execute()
        )
        return res.data[0]

    def list_conversations(self, client_id: str) -> list[dict[str, Any]]:
        return (
            self.db.table("conversations")
            .select("id, client_id, title, created_at")
            .eq("client_id", client_id)
            .order("created_at", desc=True)
            .limit(50)
            .execute()
            .data
        )

    def get_conversation(self, conversation_id: str) -> dict[str, Any] | None:
        rows = (
            self.db.table("conversations").select("*").eq("id", conversation_id).limit(1).execute()
        ).data
        return rows[0] if rows else None

    def list_messages(self, conversation_id: str) -> list[dict[str, Any]]:
        return (
            self.db.table("messages")
            .select("data, created_at")
            .eq("conversation_id", conversation_id)
            .order("id")
            .execute()
            .data
        )

    def append_messages(self, conversation_id: str, messages: list[Message]) -> None:
        if messages:
            self.db.table("messages").insert(
                [
                    {"conversation_id": conversation_id, "data": m.model_dump(mode="json")}
                    for m in messages
                ]
            ).execute()

    def set_title(self, conversation_id: str, title: str) -> None:
        self.db.table("conversations").update({"title": title}).eq("id", conversation_id).execute()


@lru_cache
def get_chat_store() -> ChatStore:
    if settings.supabase_url and settings.supabase_service_role_key:
        return SupabaseChatStore()
    return MemoryChatStore()
