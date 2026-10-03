"""radar: mock LLM과 가짜 공급자로 단계 순서·근거 검증·오류 처리를 확인한다 (실제 LLM·DB 없음)."""

import json

import pytest
from fastapi.testclient import TestClient

from app.agent.structured import _submit_model
from app.agent.types import Message, ToolCall, TurnComplete
from app.main import app
from app.services import radar

client = TestClient(app)


def parse_sse(text: str) -> list[tuple[str, dict]]:
    out = []
    for chunk in text.strip().split("\n\n"):
        if chunk.startswith(":"):
            continue
        lines = dict(line.split(": ", 1) for line in chunk.splitlines())
        out.append((lines["event"], json.loads(lines["data"])))
    return out


class FakeProvider:
    """제출 도구 이름별로 정해진 입력을 돌려준다. outputs[name] = None이면 도구를 부르지 않는다."""

    name = "fake"

    def __init__(self, outputs: dict[str, dict | None]):
        self.outputs = outputs
        self.calls: list[str] = []

    async def stream_turn(self, *, system, history, tools):
        name = tools[0].name
        self.calls.append(name)
        out = self.outputs.get(name)
        calls = [ToolCall(id=f"c{len(self.calls)}", name=name, input=out)] if out else []
        yield TurnComplete(
            message=Message(role="assistant", content="", tool_calls=calls),
            stop_reason="tool_use" if calls else "end_turn",
        )


def post(**body):
    return client.post("/api/radar/opportunities", json={"company_id": "kt-cloud", **body})


def test_companies():
    companies = client.get("/api/radar/companies").json()
    assert [c["id"] for c in companies] == ["kt", "kt-cloud", "kt-ds", "bccard", "kt-skylife"]
    assert all(c["assets"] and c["sources"] for c in companies)


def test_mock_stream_follows_contract_order(mock_llm):
    res = post(count=3)
    assert res.status_code == 200 and res.headers["content-type"].startswith("text/event-stream")
    events = parse_sse(res.text)
    names = [(e, d.get("stage"), d.get("status")) for e, d in events]
    assert names == [
        ("stage", "trend", "start"),
        ("stage", "trend", "done"),
        ("stage", "match", "start"),
        ("stage", "match", "done"),
        ("stage", "opportunity", "start"),
        ("opportunity", None, None),
        ("opportunity", None, None),
        ("opportunity", None, None),
        ("stage", "opportunity", "done"),
        ("done", None, None),
    ]
    opp = events[5][1]["opportunity"]
    assert opp["company_id"] == "kt-cloud" and opp["country"] == "KR"
    ev = opp["evidence"][0]
    assert ev["from"] == "2024-07" and ev["label"].startswith("KR ")


def test_validation_before_stream(mock_llm):
    assert client.post("/api/radar/opportunities", json={"company_id": "nope"}).status_code == 404
    assert post(country="ZZ").status_code == 404
    assert post(count=6).status_code == 422
    assert post(focus="x" * 201).status_code == 422


TRENDS = {"trends": [{"title": "실무 가이드 증가", "insight": "i", "evidence_ids": ["e1"]}] * 2}
MATCHES = {"matches": [{"trend_title": "t", "business_area": "퍼블릭 클라우드", "angle": "a"}] * 2}


def draft(**over):
    base = {
        "title": "Cloud 장애 대응 자동화",
        "trend": "t",
        "target": ["KT Cloud 운영 조직"],
        "problem": "p",
        "solution": "s",
        "kt_assets": ["전국 데이터센터", "지어낸 자산"],
        "evidence_ids": ["e1", "e999", "e1"],
        "rationale": "r",
        "impact": 4,
        "feasibility": 3,
    }
    return {**base, **over}


def test_llm_output_is_checked_against_data_and_company(use_provider):
    fake = FakeProvider(
        {
            "submit_trends": TRENDS,
            "submit_matches": MATCHES,
            "submit_opportunities": {
                "opportunities": [draft(), draft(title="근거 없음", evidence_ids=["e999"])]
            },
        }
    )
    use_provider(fake)
    events = parse_sse(post(count=3).text)
    opps = [d["opportunity"] for e, d in events if e == "opportunity"]
    assert [o["title"] for o in opps] == ["Cloud 장애 대응 자동화"]  # 근거 없는 기회는 버림
    assert opps[0]["kt_assets"] == ["전국 데이터센터"]  # 회사에 없는 자산은 버림
    assert len(opps[0]["evidence"]) == 1  # 없는 id·중복 제거, 값은 서버가 채움
    assert opps[0]["evidence"][0]["to_value"] > 0
    assert fake.calls == ["submit_trends", "submit_matches", "submit_opportunities"]
    assert events[-1][0] == "done"


def test_no_tool_call_retries_once_then_bad_output(use_provider):
    fake = FakeProvider({"submit_trends": None})
    use_provider(fake)
    events = parse_sse(post().text)
    assert events[-1] == (
        "error",
        {"code": "bad_output", "message": "AI가 결과 형식을 맞추지 못했어요. 다시 시도해 주세요."},
    )
    assert fake.calls == ["submit_trends", "submit_trends"]


def test_no_evidence_at_all_is_no_result(use_provider):
    fake = FakeProvider(
        {
            "submit_trends": TRENDS,
            "submit_matches": MATCHES,
            "submit_opportunities": {"opportunities": [draft(evidence_ids=["e999"])]},
        }
    )
    use_provider(fake)
    events = parse_sse(post().text)
    assert events[-1][0] == "error" and events[-1][1]["code"] == "no_result"
    assert ("opportunity", "done") not in [(d.get("stage"), d.get("status")) for _, d in events]


def test_submit_schema_has_no_refs():
    schema = json.dumps(_submit_model(radar.OpportunitiesOut).model_json_schema())
    assert "$ref" not in schema and "$defs" not in schema


def test_quota_checked_before_stream(mock_llm, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "chat_rate_per_ip", 0)
    assert post().status_code == 429


class ScriptedProvider:
    """호출마다 정해진 동작: 예외를 던지거나 TurnComplete를 돌려준다."""

    name = "scripted"

    def __init__(self, script):
        self.script = list(script)
        self.calls = 0

    async def stream_turn(self, *, system, history, tools):
        self.calls += 1
        step = self.script.pop(0)
        if isinstance(step, Exception):
            raise step
        name = tools[0].name
        calls = [ToolCall(id="c", name=name, input=step[1])] if step[1] else []
        message = Message(role="assistant", tool_calls=calls)
        yield TurnComplete(message=message, stop_reason=step[0])


class RateLimitedError(Exception):
    status_code = 429


def run_structured(provider, budget=None):
    import asyncio

    from app.agent.structured import CallBudget, call_structured

    events = []

    async def emit(event, data):
        events.append((event, data))

    async def go():
        return await call_structured(
            system="s",
            prompt="p",
            tool_name="submit_trends",
            description="d",
            model=radar.TrendsOut,
            emit=emit,
            budget=budget or CallBudget(),
            provider=provider,
        )

    return asyncio.run(go()), events


def test_transient_error_retries_with_event(monkeypatch):
    monkeypatch.setattr("app.agent.structured.asyncio.sleep", _no_sleep)
    provider = ScriptedProvider([RateLimitedError("429"), ("tool_use", TRENDS)])
    out, events = run_structured(provider)
    assert len(out.trends) == 2 and provider.calls == 2
    assert events == [("retry", {"code": "rate_limit", "wait_seconds": 4.0, "attempt": 1})]


def test_unparseable_tool_json_counts_as_bad_output_retry():
    provider = ScriptedProvider([ValueError("bad json"), ("tool_use", TRENDS)])
    out, _ = run_structured(provider)
    assert len(out.trends) == 2 and provider.calls == 2


def test_max_tokens_stops_without_repeating():
    from app.agent.structured import StructuredError

    provider = ScriptedProvider([("max_tokens", None), ("tool_use", TRENDS)])
    with pytest.raises(StructuredError) as e:
        run_structured(provider)
    assert e.value.code == "bad_output" and provider.calls == 1


def test_call_budget_caps_llm_calls():
    from app.agent.structured import CallBudget, StructuredError

    provider = ScriptedProvider([("end_turn", None)] * 5)
    with pytest.raises(StructuredError) as e:
        run_structured(provider, CallBudget(limit=1))
    assert e.value.code == "limit" and provider.calls == 1


def test_inline_refs_keeps_sibling_description():
    from pydantic import BaseModel, Field

    from app.agent.structured import _inline_refs

    class Inner(BaseModel):
        x: int

    class Outer(BaseModel):
        inner: Inner = Field(description="안쪽")

    schema = _inline_refs(Outer.model_json_schema())
    assert schema["properties"]["inner"]["description"] == "안쪽"
    assert schema["properties"]["inner"]["properties"]["x"]["type"] == "integer"


async def _no_sleep(_):
    return None
