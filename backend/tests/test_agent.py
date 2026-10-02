import asyncio
import json

from pydantic import BaseModel

from app.agent.loop import run_agent
from app.agent.providers.anthropic import _sanitize_raw, to_anthropic_messages
from app.agent.tools import Tool, get_tools
from app.agent.types import Message, TextDelta, ToolCall, TurnComplete, close_orphan_tool_calls


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


def test_orphan_tool_calls_closed():
    history = [
        Message(role="user", content="q"),
        Message(
            role="assistant", tool_calls=[ToolCall(id="a", name="x"), ToolCall(id="b", name="y")]
        ),
        Message(role="tool", tool_call_id="a", content="ok"),
        Message(role="user", content="다음 질문"),  # b의 결과 없이 끊긴 뒤 새 질문
    ]
    fixed = close_orphan_tool_calls(history)
    assert [(m.role, m.tool_call_id) for m in fixed] == [
        ("user", None),
        ("assistant", None),
        ("tool", "a"),
        ("tool", "b"),
        ("user", None),
    ]
    assert fixed[3].is_error and len(history) == 4  # 원본은 그대로
    out = to_anthropic_messages(history, "anthropic")
    assert [b["tool_use_id"] for b in out[2]["content"]] == ["a", "b"]


def test_calculator_blocks_huge_power():
    calc = next(t for t in get_tools() if t.name == "calculator")
    for expr in ["((9**99)**99)**99", "10**400", "(10**12+1)**2"]:
        try:
            asyncio.run(calc.run(calc.input_model(expression=expr)))
            raise AssertionError(expr)
        except ValueError:
            pass


TRIGGER = {"type": "refusal"}


def test_fallback_block_dumped_with_alias():
    from anthropic.types.beta import BetaMessage

    msg = BetaMessage.model_validate(
        {
            "id": "m",
            "type": "message",
            "role": "assistant",
            "model": "claude-opus-5-5",
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {"input_tokens": 1, "output_tokens": 1},
            "content": [
                {"type": "text", "text": "a"},
                {
                    "type": "fallback",
                    "from": {"model": "claude-opus-5-5"},
                    "to": {"model": "claude-opus-4-8"},
                    "trigger": {"type": "refusal"},
                },
                {"type": "text", "text": "b"},
            ],
        }
    )
    raw = [b.model_dump(mode="json", by_alias=True, exclude_none=True) for b in msg.content]
    fb = next(b for b in raw if b["type"] == "fallback")
    assert "from" in fb and "from_" not in fb


class _FlakyProvider:
    """처음 n번은 지정한 예외, 이후 정상 답변."""

    name = "flaky"

    def __init__(self, exc, fails=1, emit_first=False):
        self.exc, self.fails, self.emit_first, self.calls = exc, fails, emit_first, 0

    async def stream_turn(self, *, system, history, tools):
        self.calls += 1
        if self.calls <= self.fails:
            if self.emit_first:
                yield TextDelta(text="부분")
            raise self.exc
        yield TextDelta(text="ok")
        yield TurnComplete(message=Message(role="assistant", content="ok"), stop_reason="end_turn")


class _StatusError(Exception):
    def __init__(self, status, headers=None):
        self.status_code = status
        self.response = type("R", (), {"headers": headers or {}})()


def _fast_retry(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "agent_retry_delay", 0)
    monkeypatch.setattr(settings, "agent_retry_max_delay", 0)


def test_rate_limit_retried_then_success(monkeypatch):
    _fast_retry(monkeypatch)
    p = _FlakyProvider(_StatusError(429, {"retry-after": "7"}), fails=2)
    events = collect([Message(role="user", content="q")], provider=p)
    assert [e.type for e in events].count("retry") == 2
    assert events[0].data["code"] == "rate_limit"
    assert events[-1].type == "done" and p.calls == 3


def test_gives_up_with_friendly_message(monkeypatch):
    _fast_retry(monkeypatch)
    p = _FlakyProvider(_StatusError(503), fails=10)
    events = collect([Message(role="user", content="q")], provider=p)
    err = events[-1]
    assert err.type == "error" and err.data["code"] == "unavailable"
    assert "다시 시도" in err.data["message"] and "Error" not in err.data["message"]
    assert p.calls == 3  # 최초 1 + 재시도 2


def test_no_retry_after_text_or_non_retryable(monkeypatch):
    _fast_retry(monkeypatch)
    p = _FlakyProvider(_StatusError(429), fails=1, emit_first=True)
    events = collect([Message(role="user", content="q")], provider=p)
    assert "retry" not in [e.type for e in events] and events[-1].type == "error" and p.calls == 1
    p = _FlakyProvider(_StatusError(400), fails=1)
    events = collect([Message(role="user", content="q")], provider=p)
    assert events[-1].data["code"] == "bad_request" and p.calls == 1


def test_classify_retry_after_and_auth():
    from app.agent.errors import classify

    assert classify(_StatusError(429, {"retry-after": "7"})).retry_after == 7.0
    assert classify(_StatusError(401)).code == "auth"
    assert classify(RuntimeError("x")).code == "internal"
