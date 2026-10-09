import json

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
H = {"X-Client-Id": "test-client-1"}


def parse_sse(text: str) -> list[tuple[str, dict]]:
    out = []
    for chunk in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in chunk.splitlines())
        out.append((lines["event"], json.loads(lines["data"])))
    return out


def test_conversation_flow():
    conv = client.post("/api/chat/conversations", json={}, headers=H).json()
    res = client.post(
        f"/api/chat/conversations/{conv['id']}/messages", json={"content": "2+3*4 계산"}, headers=H
    )
    assert res.status_code == 200 and res.headers["content-type"].startswith("text/event-stream")
    events = parse_sse(res.text)
    assert [e for e, _ in events][-1] == "done"
    assert any(e == "tool_call" and d["name"] == "calculator" for e, d in events)

    msgs = client.get(f"/api/chat/conversations/{conv['id']}/messages", headers=H).json()
    assert [m["role"] for m in msgs] == ["user", "assistant", "tool", "assistant"]
    assert "raw" not in msgs[1]

    convs = client.get("/api/chat/conversations", headers=H).json()
    assert convs[0]["id"] == conv["id"] and convs[0]["title"] == "2+3*4 계산"


def test_other_client_cannot_access():
    conv = client.post("/api/chat/conversations", json={}, headers=H).json()
    other = {"X-Client-Id": "someone-else"}
    assert (
        client.get(f"/api/chat/conversations/{conv['id']}/messages", headers=other).status_code
        == 404
    )
    r = client.post(
        f"/api/chat/conversations/{conv['id']}/messages", json={"content": "hi"}, headers=other
    )
    assert r.status_code == 404
    assert client.get("/api/chat/conversations", headers=other).json() == []


def test_requires_client_id_and_valid_id():
    assert client.post("/api/chat/conversations", json={}).status_code == 422
    assert client.get("/api/chat/conversations/not-a-uuid/messages", headers=H).status_code == 404


def test_rate_limit(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "chat_rate_per_ip", 2)
    conv = client.post("/api/chat/conversations", json={}, headers=H).json()
    url = f"/api/chat/conversations/{conv['id']}/messages"
    codes = [client.post(url, json={"content": "hi"}, headers=H).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_conversation_length_cap(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "chat_max_messages", 2)
    conv = client.post("/api/chat/conversations", json={}, headers=H).json()
    url = f"/api/chat/conversations/{conv['id']}/messages"
    assert client.post(url, json={"content": "hi"}, headers=H).status_code == 200  # user+assistant
    assert client.post(url, json={"content": "again"}, headers=H).status_code == 409


def _new_conv_url() -> str:
    conv = client.post("/api/chat/conversations", json={}, headers=H).json()
    return f"/api/chat/conversations/{conv['id']}/messages"


def test_chat_limit_content_empty():
    """계약: content 는 1자 이상 — 빈 문자열은 422."""
    r = client.post(_new_conv_url(), json={"content": ""}, headers=H)
    assert r.status_code == 422


def test_chat_limit_content_max():
    """계약: content 최대 8000자 — 8000자는 통과, 8001자는 422."""
    url = _new_conv_url()
    assert client.post(url, json={"content": "a" * 8000}, headers=H).status_code == 200
    assert client.post(url, json={"content": "a" * 8001}, headers=H).status_code == 422


def test_chat_limit_title_max():
    """계약: title 최대 100자 — 100자는 통과, 101자는 422."""
    url = "/api/chat/conversations"
    assert client.post(url, json={"title": "t" * 100}, headers=H).status_code == 201
    assert client.post(url, json={"title": "t" * 101}, headers=H).status_code == 422


def test_search_and_export_tc_chat_search():  # TC-CHAT-SEARCH
    conv = client.post("/api/chat/conversations", json={"title": "검색용 대화"}, headers=H).json()
    client.post(
        f"/api/chat/conversations/{conv['id']}/messages",
        json={"content": "유니크키워드xyz"},
        headers=H,
    )
    ids = [
        c["id"]
        for c in client.get("/api/chat/search", params={"q": "유니크키워드XYZ"}, headers=H).json()
    ]
    assert conv["id"] in ids
    other = {"X-Client-Id": "someone-else"}
    assert (
        client.get("/api/chat/search", params={"q": "유니크키워드xyz"}, headers=other).json() == []
    )
    for q in ("", "x" * 101):
        assert client.get("/api/chat/search", params={"q": q}, headers=H).status_code == 422
    assert client.get("/api/chat/search", headers=H).status_code == 422

    res = client.get(f"/api/chat/conversations/{conv['id']}/export", headers=H)
    assert res.status_code == 200 and res.headers["content-type"].startswith("text/markdown")
    assert "# 검색용 대화" in res.text and "유니크키워드xyz" in res.text
    assert (
        client.get(f"/api/chat/conversations/{conv['id']}/export", headers=other).status_code
        == 404
    )


def _conv_with_answer(content: str = "안녕") -> str:
    conv = client.post("/api/chat/conversations", json={}, headers=H).json()
    client.post(
        f"/api/chat/conversations/{conv['id']}/messages", json={"content": content}, headers=H
    )
    return conv["id"]


def _roles(conv_id: str) -> list[str]:
    msgs = client.get(f"/api/chat/conversations/{conv_id}/messages", headers=H).json()
    return [m["role"] for m in msgs]


def test_regenerate_replaces_last_answer_tc_chat_regen():  # TC-CHAT-REGEN-1
    cid = _conv_with_answer("2+3*4 계산")  # user, assistant, tool, assistant
    assert _roles(cid) == ["user", "assistant", "tool", "assistant"]
    res = client.post(f"/api/chat/conversations/{cid}/regenerate", headers=H)
    assert res.status_code == 200 and res.headers["content-type"].startswith("text/event-stream")
    assert [e for e, _ in parse_sse(res.text)][-1] == "done"
    # 사용자 메시지는 그대로, 답변 턴은 새로 하나만 (중복 없음)
    assert _roles(cid) == ["user", "assistant", "tool", "assistant"]


def test_regenerate_without_messages_is_422_tc_chat_regen():  # TC-CHAT-REGEN-2
    conv = client.post("/api/chat/conversations", json={}, headers=H).json()
    assert (
        client.post(f"/api/chat/conversations/{conv['id']}/regenerate", headers=H).status_code
        == 422
    )


def test_regenerate_other_client_is_404_tc_chat_regen():  # TC-CHAT-REGEN-3
    cid = _conv_with_answer()
    other = {"X-Client-Id": "someone-else"}
    assert (
        client.post(f"/api/chat/conversations/{cid}/regenerate", headers=other).status_code == 404
    )
    assert (
        client.post("/api/chat/conversations/not-a-uuid/regenerate", headers=H).status_code == 404
    )


def test_regenerate_counts_toward_quota_and_keeps_answer_tc_chat_regen(
    monkeypatch,
):  # TC-CHAT-REGEN-4
    from app.core.config import settings

    monkeypatch.setattr(settings, "chat_rate_per_ip", 2)
    cid = _conv_with_answer()  # 1회
    url = f"/api/chat/conversations/{cid}/regenerate"
    assert client.post(url, headers=H).status_code == 200  # 2회
    before = _roles(cid)
    assert client.post(url, headers=H).status_code == 429  # 한도 초과
    assert _roles(cid) == before  # 한도에 걸려도 기존 답변은 지워지지 않는다


def test_stop_saves_partial_text_tc_chat_stop(monkeypatch):  # TC-CHAT-STOP
    import asyncio

    from app.agent.types import AgentEvent, Message
    from app.services import chat as service

    async def slow_agent(history):
        yield AgentEvent(type="text", data={"text": "절반만 "})
        yield AgentEvent(type="text", data={"text": "나온 답"})
        await asyncio.sleep(60)  # 사용자가 여기서 중단

    monkeypatch.setattr(service, "run_agent", slow_agent)
    conv = client.post("/api/chat/conversations", json={}, headers=H).json()
    store = service.get_chat_store()
    user = Message(role="user", content="길게 답해줘")
    store.append_messages(conv["id"], [user])

    async def go():
        stream = service._stream(conv["id"], [user])
        assert (await anext(stream)).startswith("event: text")
        await anext(stream)
        await stream.aclose()  # 클라이언트 연결 끊김 = 중단
        await asyncio.sleep(0.2)  # 취소된 생산자가 저장을 마칠 시간

    asyncio.run(go())
    rows = [r["data"] for r in store.list_messages(conv["id"])]
    assert [r["role"] for r in rows] == ["user", "assistant"]
    assert rows[1]["content"] == "절반만 나온 답"


def test_stop_during_tool_call_drops_unanswered_call_tc_chat_stop():  # TC-CHAT-STOP-2
    from app.agent.types import Message, ToolCall
    from app.services.chat import _drop_unanswered_tool_calls

    call = ToolCall(id="t1", name="calculator", input={})
    pending = Message(role="assistant", content="계산할게요", tool_calls=[call])
    done = Message(role="tool", tool_call_id="t1", content="14")
    assert _drop_unanswered_tool_calls([pending]) == []
    assert _drop_unanswered_tool_calls([pending, done]) == [pending, done]
