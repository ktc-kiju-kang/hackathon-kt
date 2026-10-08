"""사용량 한도용 클라이언트 IP: 클라이언트가 바꿀 수 있는 헤더로 한도를 우회하지 못해야 한다."""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.core.quota import client_ip
from app.main import app

client = TestClient(app)


def req(headers: dict[str, str], host: str = "10.0.0.5") -> Request:
    raw = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
    return Request({"type": "http", "headers": raw, "client": (host, 1234)})


@pytest.mark.parametrize(
    ("headers", "expected"),
    [
        (
            {"CF-Connecting-IP": "1.1.1.1", "X-Forwarded-For": "9.9.9.9, 1.1.1.1, 172.68.0.1"},
            "1.1.1.1",
        ),
        # True-Client-IP는 클라이언트가 넣을 수 있으므로 무시
        ({"True-Client-IP": "8.8.8.8", "X-Forwarded-For": "9.9.9.9, 172.68.0.1"}, "172.68.0.1"),
        # Cloudflare 헤더가 없으면 가장 가까운 프록시가 붙인 마지막 값 (첫 값은 조작 가능)
        ({"X-Forwarded-For": "9.9.9.9, 8.8.8.8, 172.68.0.1"}, "172.68.0.1"),
        ({"X-Forwarded-For": "1.1.1.1"}, "1.1.1.1"),
        # IP 형식이 아닌 값은 버린다
        ({"CF-Connecting-IP": "not-an-ip", "X-Forwarded-For": "garbage"}, "10.0.0.5"),
        ({}, "10.0.0.5"),  # 로컬·테스트
    ],
)
def test_client_ip(headers, expected):
    assert client_ip(req(headers)) == expected


def test_ipv6_grouped_by_64(monkeypatch):
    from app.core import quota
    from app.core.config import settings

    monkeypatch.setattr(settings, "chat_rate_per_ip", 2)
    quota.check_quota("2001:db8:1:2::1")
    quota.check_quota("2001:db8:1:2::ffff")
    with pytest.raises(HTTPException):
        quota.check_quota("2001:db8:1:2:abcd::9")  # 같은 /64
    quota.check_quota("2001:db8:1:3::1")  # 다른 /64


def test_stale_keys_are_swept(monkeypatch):
    from app.core import quota

    monkeypatch.setattr(quota, "_SWEEP_AT", 3)
    now = [1000.0]
    monkeypatch.setattr(quota.time, "monotonic", lambda: now[0])
    for i in range(4):
        quota.check_quota(f"1.1.1.{i}")
    now[0] += quota._WINDOW + 1
    quota.check_quota("2.2.2.2")
    assert set(quota._hits) == {"2.2.2.2"}


def test_spoofed_forwarded_for_does_not_bypass_quota(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "chat_rate_per_ip", 2)
    owner = {"X-Client-Id": "quota-client"}
    conv = client.post("/api/chat/conversations", json={}, headers=owner).json()

    def call(spoof: str, count: int) -> int:
        headers = {
            "CF-Connecting-IP": "1.1.1.1",
            "X-Forwarded-For": f"{spoof}, 1.1.1.1, 172.68.0.1",
        }
        url = f"/api/chat/conversations/{conv['id']}/messages"
        body = {"content": f"{count} 더하기 1"}
        return client.post(url, json=body, headers={**owner, **headers}).status_code

    assert [call(f"9.9.9.{i}", 3 + i) for i in range(3)] == [200, 200, 429]


def test_health_shows_own_ip():
    res = client.get("/api/health", headers={"CF-Connecting-IP": "1.1.1.1"})
    assert res.json()["client_ip"] == "1.1.1.1"
    assert res.headers["cache-control"] == "no-store"
