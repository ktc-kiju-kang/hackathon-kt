from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "supabase_url", "")  # 로컬 .env와 무관하게
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert "time" in body
    assert body["db"] == "unconfigured"
    assert body["llm"] in ("anthropic", "mock")


def test_health_version(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "render_git_commit", "abc123")
    assert client.get("/api/health").json()["version"] == "abc123"


def test_health_db_ok(monkeypatch):
    from app.services import health

    monkeypatch.setattr(health, "check_db", lambda: "ok")
    assert client.get("/api/health").json()["db"] == "ok"


def test_check_db_error(monkeypatch):
    from app.core.config import settings
    from app.services import health

    monkeypatch.setattr(settings, "supabase_url", "https://example.supabase.co")
    monkeypatch.setattr(settings, "supabase_service_role_key", "bad")

    def boom():
        raise RuntimeError("invalid key")

    monkeypatch.setattr(health, "get_supabase", boom)
    assert health.check_db() == "error"


def _jwt(role: str) -> str:
    import base64
    import json

    body = base64.urlsafe_b64encode(json.dumps({"role": role}).encode()).decode().rstrip("=")
    return f"eyJhbGciOiJIUzI1NiJ9.{body}.sig"


def test_key_role_detection():
    from app.services.health import key_role

    assert key_role(_jwt("service_role")) == "service_role"
    assert key_role(_jwt("anon")) == "anon"
    assert key_role("sb_secret_abc") == "service_role"
    assert key_role("sb_publishable_abc") == "anon"
    assert key_role("garbage") is None


def test_check_db_rejects_anon_key(monkeypatch):
    from app.core.config import settings
    from app.services import health

    monkeypatch.setattr(settings, "supabase_url", "https://example.supabase.co")
    for key in (_jwt("anon"), "sb_publishable_x"):
        monkeypatch.setattr(settings, "supabase_service_role_key", key)
        monkeypatch.setattr(health, "get_supabase", lambda: (_ for _ in ()).throw(AssertionError))
        assert health.check_db() == "error"  # DB 조회 전에 걸러진다
