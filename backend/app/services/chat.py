import asyncio
import json
import uuid
from collections.abc import AsyncGenerator, AsyncIterator

from fastapi import HTTPException

from app.agent.loop import run_agent
from app.agent.types import AgentEvent, Message
from app.core.config import settings
from app.core.quota import check_quota
from app.schemas.chat import ChatMessage, Conversation
from app.services.chat_store import get_chat_store

_inflight: dict[
    str, asyncio.Task[None]
] = {}  # 대화별 진행 중 생산자 (중단 저장이 끝나길 기다리는 데 쓴다)
PING_INTERVAL = 15.0  # 모델 생각·도구 실행 중에도 연결이 끊기지 않게 SSE 주석을 보낸다


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False


def _owned(conversation_id: str, client_id: str) -> dict:
    """권한 체크: service_role은 RLS를 우회하므로 여기서 소유자를 확인한다."""
    store = get_chat_store()
    conv = store.get_conversation(conversation_id) if _is_uuid(conversation_id) else None
    if conv is None or conv["client_id"] != client_id:
        raise HTTPException(status_code=404, detail="conversation not found")
    return conv


def create_conversation(client_id: str, title: str | None) -> Conversation:
    return Conversation(**get_chat_store().create_conversation(client_id, title))


def list_conversations(client_id: str) -> list[Conversation]:
    return [Conversation(**c) for c in get_chat_store().list_conversations(client_id)]


def search_conversations(client_id: str, q: str) -> list[Conversation]:
    return [Conversation(**c) for c in get_chat_store().search_conversations(client_id, q)]


def export_markdown(conversation_id: str, client_id: str) -> str:
    conv = _owned(conversation_id, client_id)
    lines = [f"# {conv['title'] or '제목 없음'}", ""]
    labels = {"user": "사용자", "assistant": "어시스턴트", "tool": "도구"}
    for m in list_messages(conversation_id, client_id):
        lines += [f"## {labels[m.role]}", "", m.content, ""]
    return "\n".join(lines)


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
    DB 호출(psycopg 동기 연결)은 동기라 모두 스레드에서 호출한다 (다른 스트림을 막지 않게).
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

    return _stream(conversation_id, history)


def _stream(conversation_id: str, history: list[Message]) -> AsyncGenerator[str, None]:
    """history를 에이전트에 넣어 SSE 문자열을 스트리밍하고, 새 메시지를 턴마다 저장한다."""
    store = get_chat_store()

    async def events() -> AsyncGenerator[str, None]:
        queue: asyncio.Queue[AgentEvent | None] = asyncio.Queue()

        async def produce() -> None:
            saved = len(history)
            partial: list[str] = []  # 아직 message로 확정되지 않은 스트리밍 텍스트
            try:
                async for ev in run_agent(history):
                    if ev.type == "text":
                        partial.append(ev.data.get("text", ""))
                    if ev.type in ("message", "tool_result", "done", "error"):
                        # 턴마다 새 메시지 저장 → 중간에 끊겨도 진행분은 남는다
                        new = history[saved:]
                        saved = len(history)
                        partial.clear()
                        await asyncio.to_thread(store.append_messages, conversation_id, new)
                    await queue.put(ev)
            except asyncio.CancelledError:
                # 사용자가 중단: 그때까지 만든 텍스트도 남긴다
                new = history[saved:]
                if text := "".join(partial).strip():
                    new = [*new, Message(role="assistant", content=text)]
                await asyncio.shield(
                    asyncio.to_thread(store.append_messages, conversation_id, new)
                )
                raise
            finally:
                await queue.put(None)

        task = asyncio.create_task(produce())
        _inflight[conversation_id] = task
        task.add_done_callback(
            lambda t: _inflight.get(conversation_id) is t and _inflight.pop(conversation_id)
        )
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


async def regenerate_message(conversation_id: str, client_id: str, ip: str) -> AsyncIterator[str]:
    """마지막 사용자 메시지에 대한 assistant 응답을 지우고 새로 만든다 (SSE).

    권한·한도 체크를 지우기 전에 끝낸다 — 한도에 걸려도 기존 답변은 남는다.
    """
    await asyncio.to_thread(_owned, conversation_id, client_id)
    if pending := _inflight.get(
        conversation_id
    ):  # 방금 중단한 스트림의 부분 저장이 끝나길 잠깐 기다린다
        await asyncio.wait({pending}, timeout=5)
    history = await asyncio.to_thread(_history, conversation_id)
    last_user = max((i for i, m in enumerate(history) if m.role == "user"), default=-1)
    if last_user < 0:
        raise HTTPException(status_code=422, detail="다시 생성할 메시지가 없어요")
    check_quota(ip)
    await asyncio.to_thread(get_chat_store().truncate_after_last_user, conversation_id)
    return _stream(conversation_id, history[: last_user + 1])
