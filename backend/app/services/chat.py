import asyncio
import json
import uuid
from collections.abc import AsyncIterator

from fastapi import HTTPException

from app.agent.loop import run_agent
from app.agent.types import Message
from app.schemas.chat import ChatMessage, Conversation
from app.services.chat_store import get_chat_store


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False


def _owned(conversation_id: str, client_id: str) -> dict:
    """권한 체크: service_role은 RLS를 우회하므로 여기서 소유자를 확인한다."""
    conv = get_chat_store().get_conversation(conversation_id) if _is_uuid(conversation_id) else None
    if conv is None or conv["client_id"] != client_id:
        raise HTTPException(status_code=404, detail="conversation not found")
    return conv


def create_conversation(client_id: str, title: str | None) -> Conversation:
    return Conversation(**get_chat_store().create_conversation(client_id, title))


def list_conversations(client_id: str) -> list[Conversation]:
    return [Conversation(**c) for c in get_chat_store().list_conversations(client_id)]


def _history(conversation_id: str) -> list[Message]:
    return [
        Message.model_validate(r["data"]) for r in get_chat_store().list_messages(conversation_id)
    ]


def list_messages(conversation_id: str, client_id: str) -> list[ChatMessage]:
    _owned(conversation_id, client_id)
    out = []
    for r in get_chat_store().list_messages(conversation_id):
        m = Message.model_validate(r["data"])
        out.append(
            ChatMessage(
                **m.model_dump(include={"role", "content", "tool_call_id", "is_error"}),
                tool_calls=[c.model_dump() for c in m.tool_calls],
                created_at=r.get("created_at"),
            )
        )
    return out


async def send_message(conversation_id: str, client_id: str, content: str) -> AsyncIterator[str]:
    """사용자 메시지를 저장하고 에이전트를 돌려 SSE 문자열을 스트리밍한다.

    권한 체크는 스트림 시작 전에 끝낸다 (스트림 도중엔 HTTP 상태코드를 바꿀 수 없음).
    """
    conv = _owned(conversation_id, client_id)
    store = get_chat_store()
    history = _history(conversation_id)
    user_msg = Message(role="user", content=content)
    history.append(user_msg)
    store.append_messages(conversation_id, [user_msg])
    if not conv.get("title"):
        store.set_title(conversation_id, content[:40])

    async def events() -> AsyncIterator[str]:
        saved = len(history)
        async for ev in run_agent(history):
            if ev.type in ("message", "tool_result", "done", "error"):
                # 턴이 끝날 때마다 새 메시지 저장 → 중간에 끊겨도 진행분은 남는다
                await asyncio.to_thread(store.append_messages, conversation_id, history[saved:])
                saved = len(history)
            data = json.dumps(ev.data, ensure_ascii=False, default=str)
            yield f"event: {ev.type}\ndata: {data}\n\n"

    return events()
