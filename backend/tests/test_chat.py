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
