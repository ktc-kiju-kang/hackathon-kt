from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "supabase_url", "")  # 로컬 .env와 무관하게
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert "time" in body
    assert body["db"] == "unconfigured"


def test_health_version(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "render_git_commit", "abc123")
    assert client.get("/api/health").json()["version"] == "abc123"


def test_health_db_ok(monkeypatch):
    from app.services import health

    monkeypatch.setattr(health, "check_db", lambda: "ok")
    assert client.get("/api/health").json()["db"] == "ok"


def test_check_db_error(monkeypatch):
    from app.config import settings
    from app.services import health

    monkeypatch.setattr(settings, "supabase_url", "https://example.supabase.co")
    monkeypatch.setattr(settings, "supabase_service_role_key", "bad")

    def boom():
        raise RuntimeError("invalid key")

    monkeypatch.setattr(health, "get_supabase", boom)
    assert health.check_db() == "error"
