from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert "time" in body


def test_health_version(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "render_git_commit", "abc123")
    assert client.get("/api/health").json()["version"] == "abc123"
