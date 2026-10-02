"""단계 파이프라인 module: 이벤트 순서·mock 폴백·후처리·provider 주입을 직접 확인한다."""

import asyncio
import json

import pytest
from pydantic import BaseModel

from app.agent.providers.mock import MockProvider
from app.agent.stages import StageRunner, stream_stages
from app.agent.structured import CallBudget, StructuredError
from app.agent.types import Message, ToolCall, TurnComplete


class Out(BaseModel):
    n: int


class FakeProvider:
    name = "fake"

    def __init__(self, payload: dict | None):
        self.payload = payload
        self.calls = 0

    async def stream_turn(self, *, system, history, tools):
        self.calls += 1
        name = tools[0].name
        calls = [ToolCall(id="c", name=name, input=self.payload)] if self.payload else []
        yield TurnComplete(
            message=Message(role="assistant", tool_calls=calls),
            stop_reason="tool_use" if calls else "end_turn",
        )


def make_runner(provider, limit: int | None = None):
    events: list[tuple[str, dict]] = []

    async def emit(event, data):
        events.append((event, data))

    return StageRunner(emit, CallBudget(limit), provider, system="s"), events


def run_stage(runner, **over):
    kwargs = dict(
        tool_name="submit_out",
        description="d",
        output=Out,
        prompt=lambda: "p",
        mock=lambda: Out(n=0),
        summary=lambda out: f"n={out.n}",
    )
    return asyncio.run(runner.run("s1", **{**kwargs, **over}))


def test_llm_stage_emits_start_then_done_with_summary():
    provider = FakeProvider({"n": 7})
    runner, events = make_runner(provider)
    out = run_stage(runner)
    assert out.n == 7 and provider.calls == 1
    assert events == [
        ("stage", {"stage": "s1", "status": "start"}),
        ("stage", {"stage": "s1", "status": "done", "summary": "n=7"}),
    ]


def test_mock_provider_skips_llm_and_prompt():
    def boom() -> str:
        raise AssertionError("mock에서는 프롬프트를 만들지 않는다")

    runner, events = make_runner(MockProvider())
    out = run_stage(runner, prompt=boom, mock=lambda: Out(n=3))
    assert out.n == 3
    assert [e["status"] for _, e in events] == ["start", "done"]


def test_async_summary_can_emit_between_start_and_done():
    runner, events = make_runner(FakeProvider({"n": 1}))

    async def send(out: Out) -> str:
        await runner.emit("item", {"n": out.n})
        return "sent"

    run_stage(runner, summary=send)
    assert [name for name, _ in events] == ["stage", "item", "stage"]  # start → item → done
    assert events[-1][1]["summary"] == "sent"


def test_summary_error_prevents_done():
    runner, events = make_runner(FakeProvider({"n": 1}))

    def fail(_):
        raise StructuredError("no_result", "비었어요")

    with pytest.raises(StructuredError):
        run_stage(runner, summary=fail)
    assert [e["status"] for _, e in events] == ["start"]  # done은 나가지 않는다


def test_bad_output_raises_after_one_retry():
    provider = FakeProvider(None)  # 도구를 부르지 않음
    runner, _ = make_runner(provider)
    with pytest.raises(StructuredError) as e:
        run_stage(runner)
    assert e.value.code == "bad_output" and provider.calls == 2


def test_budget_is_shared_across_stages():
    provider = FakeProvider({"n": 1})
    runner, _ = make_runner(provider, limit=1)
    run_stage(runner)  # 1회 사용
    with pytest.raises(StructuredError) as e:
        run_stage(runner)  # 같은 예산이라 두 번째는 한도 초과
    assert e.value.code == "limit" and provider.calls == 1


def test_stream_stages_uses_injected_provider_without_patching():
    provider = FakeProvider({"n": 5})

    async def run(runner: StageRunner) -> None:
        out = await runner.run(
            "s1",
            tool_name="submit_out",
            description="d",
            output=Out,
            prompt=lambda: "p",
            mock=lambda: Out(n=0),
            summary=lambda o: f"n={o.n}",
        )
        await runner.emit("done", {"n": out.n})

    async def collect() -> str:
        return "".join([c async for c in stream_stages(run, system="s", provider=provider)])

    text = asyncio.run(collect())
    frames = [f for f in text.split("\n\n") if f and not f.startswith(":")]
    parsed = [(f.splitlines()[0][7:], json.loads(f.splitlines()[1][6:])) for f in frames]
    assert [name for name, _ in parsed] == ["stage", "stage", "done"]
    assert parsed[-1][1] == {"n": 5} and provider.calls == 1


def test_stream_stages_turns_structured_error_into_error_event():
    async def run(runner: StageRunner) -> None:
        raise StructuredError("limit", "한도")

    async def collect() -> str:
        return "".join([c async for c in stream_stages(run, system="s", provider=MockProvider())])

    text = asyncio.run(collect())
    assert text.startswith("event: error") and '"code": "limit"' in text


def test_stream_stages_default_provider_comes_from_get_provider(monkeypatch):
    seen = []

    async def run(runner: StageRunner) -> None:
        seen.append(runner.provider)

    provider = FakeProvider({"n": 1})
    monkeypatch.setattr("app.agent.stages.get_provider", lambda: provider)

    async def collect() -> None:
        async for _ in stream_stages(run, system="s"):  # provider 인자 없음
            pass

    asyncio.run(collect())
    assert seen == [provider]


def test_stream_stages_passes_max_calls_to_budget():
    seen = []

    async def run(runner: StageRunner) -> None:
        seen.append(runner.budget.remaining)

    async def collect() -> None:
        async for _ in stream_stages(run, system="s", max_calls=3, provider=MockProvider()):
            pass

    asyncio.run(collect())
    assert seen == [3]
