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
