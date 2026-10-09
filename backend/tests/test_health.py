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


def test_tc_health_1_llm_mode_mock():  # TC-HEALTH-1: 키가 없으면 mock
    body = client.get("/api/health").json()
    assert (body["llm"], body["llm_mode"]) == ("mock", "mock")


def test_tc_health_2_llm_mode_real(
    monkeypatch,
):  # TC-HEALTH-2: 실제 공급자면 real, 키는 응답에 없음
    from app.services import health

    monkeypatch.setattr(health, "_llm_name", lambda: "anthropic")
    res = client.get("/api/health")
    assert res.json()["llm_mode"] == "real"
    assert "key" not in res.text.lower()


def test_tc_health_3_llm_misconfigured(monkeypatch):  # TC-HEALTH-3: 잘못된 LLM_PROVIDER여도 200
    from app.core.config import settings

    monkeypatch.setattr(settings, "llm_provider", "nope")
    res = client.get("/api/health")
    assert res.status_code == 200
    assert (res.json()["llm"], res.json()["llm_mode"]) == (None, None)


def test_tc_health_4_db_down_still_200(
    monkeypatch,
):  # TC-HEALTH-4: DB 연결 실패여도 200 + db=error
    from app.services import health

    def boom():
        raise RuntimeError("connection refused")

    monkeypatch.setattr(health, "get_db", boom)
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["db"] == "error"
    assert body["uptime_seconds"] >= 0  # 기존 필드 유지
