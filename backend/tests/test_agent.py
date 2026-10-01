import asyncio
import json

from pydantic import BaseModel

from app.agent.loop import run_agent
from app.agent.providers.anthropic import _sanitize_raw, to_anthropic_messages
from app.agent.tools import Tool, get_tools
from app.agent.types import Message, TextDelta, ToolCall, TurnComplete


def collect(history, **kw):
    async def go():
        return [ev async for ev in run_agent(history, **kw)]

    return asyncio.run(go())


def test_tools_registered():
    names = {t.name for t in get_tools()}
    assert {"get_current_time", "calculator"} <= names


def test_plain_answer():
    history = [Message(role="user", content="안녕")]
    events = collect(history)
    assert events[-1].type == "done"
    assert any(e.type == "text" for e in events)
    assert [m.role for m in history] == ["user", "assistant"]


def test_tool_loop_calculator():
    history = [Message(role="user", content="1200 * 3 / 4 계산해줘")]
    events = collect(history)
    types = [e.type for e in events]
    assert "tool_call" in types and "tool_result" in types and types[-1] == "done"
    result = next(e for e in events if e.type == "tool_result").data
    assert json.loads(result["content"])["result"] == 900
    assert [m.role for m in history] == ["user", "assistant", "tool", "assistant"]


class _ScriptedProvider:
    """정해진 tool_call을 한 번 내고, 다음 턴엔 끝내는 가짜 공급자."""

    name = "scripted"

    def __init__(self, call: ToolCall):
        self.call = call

    async def stream_turn(self, *, system, history, tools):
        if history[-1].role == "tool":
            yield TextDelta(text="끝")
            yield TurnComplete(
                message=Message(role="assistant", content="끝"), stop_reason="end_turn"
            )
        else:
            yield TurnComplete(
                message=Message(role="assistant", tool_calls=[self.call]), stop_reason="tool_use"
            )


def test_invalid_tool_input_returns_error_result():
    bad = ToolCall(id="t1", name="calculator", input={"expression": 123, "x": 1})
    history = [Message(role="user", content="q")]
    events = collect(history, provider=_ScriptedProvider(bad))
    res = next(e for e in events if e.type == "tool_result").data
    assert res["is_error"] and "INVALID_INPUT" in res["content"]
    assert events[-1].type == "done"


def test_tool_exception_and_unknown_tool():
    class In(BaseModel):
        pass

    async def boom(_):
        raise RuntimeError("down")

    tools = (Tool(name="boom", description="d", input_model=In, run=boom),)
    for call in (ToolCall(id="a", name="boom"), ToolCall(id="b", name="nope")):
        events = collect(
            [Message(role="user", content="q")], provider=_ScriptedProvider(call), tools=tools
        )
        res = next(e for e in events if e.type == "tool_result").data
        assert res["is_error"]


def test_calculator_rejects_code():
    calc = next(t for t in get_tools() if t.name == "calculator")
    args = calc.input_model(expression="__import__('os').system('ls')")
    try:
        asyncio.run(calc.run(args))
        raise AssertionError("should fail")
    except ValueError:
        pass


def test_anthropic_message_conversion():
    history = [
        Message(role="user", content="q"),
        Message(
            role="assistant",
            tool_calls=[ToolCall(id="t1", name="a"), ToolCall(id="t2", name="b")],
            provider="anthropic",
            raw=[
                {"type": "thinking", "thinking": "", "signature": "s"},
                {"type": "tool_use", "id": "t1", "name": "a", "input": {}},
                {"type": "tool_use", "id": "t2", "name": "b", "input": {}},
            ],
        ),
        Message(role="tool", tool_call_id="t1", content="r1"),
        Message(role="tool", tool_call_id="t2", content="r2", is_error=True),
    ]
    out = to_anthropic_messages(history, "anthropic")
    assert out[1]["content"][0]["type"] == "thinking"  # 원본 그대로 재전송
    assert len(out) == 3 and [b["tool_use_id"] for b in out[2]["content"]] == ["t1", "t2"]
    # 다른 공급자에서 온 기록이면 중립 형식으로 변환
    assert to_anthropic_messages(history, "other")[1]["content"][0]["type"] == "tool_use"


def test_sanitize_after_fallback():
    blocks = [
        {"type": "thinking"},
        {"type": "text", "text": "a"},
        {"type": "fallback"},
        {"type": "thinking"},
        {"type": "text", "text": "b"},
    ]
    assert [b["type"] for b in _sanitize_raw(blocks)] == ["text", "fallback", "thinking", "text"]
