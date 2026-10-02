"""trends: 레포에 포함된 실제 Signals CSV로 돈다 (DB·외부 API 없음)."""

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.trends import EvidenceRef
from app.services.trends import resolve_evidence

client = TestClient(app)


def test_meta():
    meta = client.get("/api/trends/meta").json()
    assert meta["months"] == {"from": "2024-07", "to": "2026-06"}
    assert "KR" in meta["countries"] and "US" in meta["countries"]
    assert len(meta["topics"]) == 7
    assert meta["source"]["license"] == "CC BY 4.0"


def test_series_topic_work_related():
    res = client.get(
        "/api/trends/series",
        params={"dimension": "topic", "country": "KR", "work_related": 1, "from": "2026-06"},
    )
    assert res.status_code == 200
    points = res.json()["points"]
    assert {p["month"] for p in points} == {"2026-06"}
    assert abs(sum(p["share"] for p in points) - 1) < 0.02  # work_related 그룹 안에서 정규화


def test_series_validation():
    def status(**params):
        return client.get("/api/trends/series", params=params).status_code

    assert status(dimension="ask_do_express") == 422  # work_related 필수
    assert status(dimension="ask_do_express", work_related=0) == 200
    assert status(dimension="work_related", work_related=1) == 422
    assert status(dimension="topic", **{"from": "2026-06", "to": "2024-07"}) == 422
    assert status(dimension="topic", country="kr") == 422
    assert status(dimension="topic", country="ZZ") == 404


def test_summary_kr():
    s = client.get("/api/trends/summary", params={"country": "KR", "months": 23}).json()
    assert s["period"] == {"from": "2024-07", "to": "2026-06"}
    changes = [t["change_pp"] for t in s["topics"]]
    assert changes == sorted(changes, reverse=True)
    assert s["topics"][0]["topic"] == "Practical Guidance"
    assert s["usage_rank"] == {
        "quarter": "2026-04",
        "rank": 25,
        "previous_quarter": "2025-01",
        "previous_rank": 57,
    }
    assert client.get("/api/trends/summary").json()["usage_rank"] is None


def test_resolve_evidence_fills_values_and_drops_invalid():
    refs = [
        EvidenceRef(metric="topic_share", key="Practical Guidance", country="KR"),
        EvidenceRef(metric="usage_rank", country="KR"),
        EvidenceRef(metric="work_share", country=None),
        EvidenceRef(metric="topic_share", key="Practical Guidance", country="KR"),  # 중복
        EvidenceRef(metric="topic_share", key="없는 주제", country="KR"),
        EvidenceRef(metric="topic_share", key="Writing", country="US"),  # 허용 국가 아님
        EvidenceRef(metric="usage_rank", country=None),  # 전 세계 순위 없음
    ]
    out = resolve_evidence(refs, {"KR", None})
    assert [(e.metric, e.country) for e in out] == [
        ("topic_share", "KR"),
        ("usage_rank", "KR"),
        ("work_share", None),
    ]
    assert out[0].label == "KR 메시지 중 Practical Guidance 23.2% → 34.1% (2024-07 → 2026-06)"
    assert (out[0].from_value, out[0].to_value, out[0].change_pp) == (0.232, 0.341, 10.9)
    assert out[1].from_value == 57 and out[1].to_value == 25 and out[1].change_pp is None
