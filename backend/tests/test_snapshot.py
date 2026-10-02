"""데모 스냅샷: 생성 스크립트(mock)로 만든 파일을 API가 계약 형태로 돌려주는지 (LLM·DB 없음)."""

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.agent.providers.mock import MockProvider
from app.main import app
from app.services import snapshot
from evals.make_demo_snapshot import build

client = TestClient(app)


@pytest.fixture
def demo_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(snapshot, "DEMO_DIR", tmp_path)
    snapshot._load_all.cache_clear()
    yield tmp_path
    snapshot._load_all.cache_clear()


def test_snapshot_round_trip(demo_dir):
    snap = asyncio.run(build("kt-cloud", 3, MockProvider()))
    snapshot.save(snap)
    assert (demo_dir / "kt-cloud.json").exists()

    res = client.get("/api/radar/snapshot/kt-cloud").json()
    assert res["company_id"] == "kt-cloud" and res["country"] == "KR"
    assert res["snapshot"]["model"] == "mock"
    assert len(res["opportunities"]) == 3 and "products" not in res
    opp = res["opportunities"][0]
    assert opp["evidence"][0]["from"] == "2024-07"  # alias 그대로

    card = client.get(f"/api/product/snapshot/{opp['id']}").json()
    assert card["product"]["opportunity_id"] == opp["id"]
    assert card["snapshot"] == res["snapshot"]
    assert "in" in card["product"]["mvp_scope"]  # alias 그대로


def test_snapshot_missing_is_404(demo_dir):
    assert client.get("/api/radar/snapshot/kt").status_code == 404
    assert client.get("/api/product/snapshot/opp_none").status_code == 404


def test_snapshot_does_not_use_quota(demo_dir, monkeypatch):
    from app.config import settings

    snapshot.save(asyncio.run(build("kt-cloud", 3, MockProvider())))
    monkeypatch.setattr(settings, "chat_rate_per_ip", 0)  # 생성 API라면 바로 429
    assert client.get("/api/radar/snapshot/kt-cloud").status_code == 200
