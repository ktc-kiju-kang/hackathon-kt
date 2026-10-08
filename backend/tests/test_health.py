from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert "time" in body
    assert body["db"] == "ok"  # conftest가 테스트마다 새 schema를 준다
    assert body["llm"] == "mock"


def test_health_version(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "app_version", "abc123")
    assert client.get("/api/health").json()["version"] == "abc123"


def test_check_db_error(monkeypatch):
    from app.services import health

    def boom():
        raise RuntimeError("disk")

    monkeypatch.setattr(health, "get_db", boom)
    assert health.check_db() == "error"


def test_health_uptime_seconds():
    uptime = client.get("/api/health").json()["uptime_seconds"]
    assert isinstance(uptime, int)
    assert uptime >= 0


def test_health_uptime_uses_started_at(monkeypatch):
    import time

    from app.services import health

    monkeypatch.setattr(health, "_STARTED_AT", time.monotonic() - 100)
    uptime = client.get("/api/health").json()["uptime_seconds"]
    assert 100 <= uptime < 110
