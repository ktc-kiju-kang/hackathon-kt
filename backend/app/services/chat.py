import asyncio
import json
import uuid
from collections.abc import AsyncIterator

from fastapi import HTTPException

from app.agent.loop import run_agent
from app.agent.types import AgentEvent, Message
from app.core.config import settings
from app.core.quota import check_quota
from app.schemas.chat import ChatMessage, Conversation
from app.services.chat_store import get_chat_store

PING_INTERVAL = 15.0  # 모델 생각·도구 실행 중에도 연결이 끊기지 않게 SSE 주석을 보낸다


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


def _sse(ev: AgentEvent) -> str:
    return f"event: {ev.type}\ndata: {json.dumps(ev.data, ensure_ascii=False, default=str)}\n\n"


async def send_message(
    conversation_id: str, client_id: str, content: str, ip: str
) -> AsyncIterator[str]:
    """사용자 메시지를 저장하고 에이전트를 돌려 SSE 문자열을 스트리밍한다.

    권한·한도 체크는 스트림 시작 전에 끝낸다 (스트림 도중엔 HTTP 상태코드를 바꿀 수 없음).
    Supabase 클라이언트는 동기라 모두 스레드에서 호출한다 (다른 스트림을 막지 않게).
    """
    conv = await asyncio.to_thread(_owned, conversation_id, client_id)
    history = await asyncio.to_thread(_history, conversation_id)
    if len(history) >= settings.chat_max_messages:
        # 앞부분을 잘라 보내면 LLM 쪽 기록이 '수정'된 것이 되므로, 새 대화를 시작하게 한다
        raise HTTPException(status_code=409, detail="대화가 너무 깁니다. 새 대화를 시작하세요")
    check_quota(ip)

    store = get_chat_store()
    user_msg = Message(role="user", content=content)
    history.append(user_msg)
    await asyncio.to_thread(store.append_messages, conversation_id, [user_msg])
    if not conv.get("title"):
        await asyncio.to_thread(store.set_title, conversation_id, content[:40])

    async def events() -> AsyncIterator[str]:
        queue: asyncio.Queue[AgentEvent | None] = asyncio.Queue()

        async def produce() -> None:
            saved = len(history)
            try:
                async for ev in run_agent(history):
                    if ev.type in ("message", "tool_result", "done", "error"):
                        # 턴마다 새 메시지 저장 → 중간에 끊겨도 진행분은 남는다
                        new = history[saved:]
                        saved = len(history)
                        await asyncio.to_thread(store.append_messages, conversation_id, new)
                    await queue.put(ev)
            finally:
                await queue.put(None)

        task = asyncio.create_task(produce())
        try:
            while True:
                try:
                    ev = await asyncio.wait_for(queue.get(), timeout=PING_INTERVAL)
                except TimeoutError:
                    yield ": ping\n\n"
                    continue
                if ev is None:
                    break
                yield _sse(ev)
        finally:
            task.cancel()  # 클라이언트가 끊으면 LLM 호출도 멈춘다 (비용 절약)

    return events()
