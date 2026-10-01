"""Gemini(OpenAI 호환) 어댑터 — 실제 API 대신 스트림 조각을 흉내 낸 가짜 클라이언트로 검증."""

import asyncio
import json

from openai.types.chat import ChatCompletionChunk

from app.agent.loop import run_agent
from app.agent.providers.openai_compat import OpenAICompatProvider, to_openai_messages
from app.agent.types import Message, ToolCall

SIG = {"google": {"thought_signature": "SIG123"}}


def chunk(delta=None, finish=None, usage=None):
    data = {"id": "c", "object": "chat.completion.chunk", "created": 0, "model": "m", "choices": []}
    if delta is not None or finish:
        data["choices"] = [{"index": 0, "delta": delta or {}, "finish_reason": finish}]
    if usage:
        data["usage"] = usage
    return ChatCompletionChunk.model_validate(data)


class FakeClient:
    """요청을 기록하고, 정해 둔 스트림을 순서대로 돌려준다."""

    def __init__(self, streams):
        self.streams = list(streams)
        self.requests = []
        self.chat = self
        self.completions = self

    async def create(self, **params):
        self.requests.append(json.loads(json.dumps(params)))
        chunks = self.streams.pop(0)

        async def gen():
            for c in chunks:
                yield c

        return gen()


TOOL_TURN = [
    chunk({"role": "assistant", "content": "계산할게요. "}),
    chunk(
        {
            "tool_calls": [
                {
                    "index": 0,
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "calculator", "arguments": '{"expression": '},
                    "extra_content": SIG,
                }
            ]
        }
    ),
    chunk({"tool_calls": [{"index": 0, "function": {"arguments": '"6*7"}'}}]}),
    chunk(finish="tool_calls"),
    chunk(usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}),
]
FINAL_TURN = [chunk({"content": "답은 42입니다."}), chunk(finish="stop")]


def run(client, text="6*7?"):
    provider = OpenAICompatProvider(preset="gemini", client=client)
    history = [Message(role="user", content=text)]

    async def go():
        return [ev async for ev in run_agent(history, provider=provider)]

    return provider, history, asyncio.run(go())


def test_tool_loop_and_signature_echo():
    client = FakeClient([TOOL_TURN, FINAL_TURN])
    provider, history, events = run(client)

    result = next(e for e in events if e.type == "tool_result").data
    assert json.loads(result["content"])["result"] == 42
    assert events[-1].type == "done"
    assert (
        "".join(e.data["text"] for e in events if e.type == "text") == "계산할게요. 답은 42입니다."
    )

    first = client.requests[0]
    assert first["model"] == "gemini-3.8-flash" and first["reasoning_effort"] == "medium"
    assert first["messages"][0]["role"] == "system"
    assert "title" not in json.dumps(first["tools"])

    # 두 번째 요청: assistant tool_call이 thought signature를 포함해 그대로 재전송된다
    second = client.requests[1]["messages"]
    assistant = next(m for m in second if m["role"] == "assistant")
    call = assistant["tool_calls"][0]
    assert call["extra_content"] == SIG
    assert call["function"] == {"name": "calculator", "arguments": '{"expression": "6*7"}'}
    assert second[-1] == {"role": "tool", "tool_call_id": "call_1", "content": result["content"]}


def test_invalid_json_arguments_not_executed():
    bad = [
        chunk(
            {
                "tool_calls": [
                    {
                        "index": 0,
                        "id": "c1",
                        "type": "function",
                        "function": {"name": "get_current_time", "arguments": "{oops"},
                    }
                ]
            }
        ),
        chunk(finish="tool_calls"),
    ]
    client = FakeClient([bad, FINAL_TURN])
    _, _, events = run(client, "몇 시야")
    res = next(e for e in events if e.type == "tool_result").data
    assert res["is_error"] and "INVALID_JSON" in res["content"]


def test_length_and_content_filter():
    for finish, expected in (("length", "error"), ("content_filter", "error")):
        turn = [
            chunk(
                {
                    "tool_calls": [
                        {
                            "index": 0,
                            "id": "c1",
                            "type": "function",
                            "function": {"name": "calculator", "arguments": '{"expr'},
                        }
                    ]
                }
            ),
            chunk(finish=finish),
        ]
        _, history, events = run(FakeClient([turn]))
        assert events[-1].type == expected
        assert not any(e.type == "tool_result" for e in events)  # 잘린/거절된 호출은 실행 안 함


def test_history_from_other_provider_and_orphans():
    history = [
        Message(role="user", content="q"),
        Message(
            role="assistant",
            provider="anthropic",
            raw=[{"type": "thinking"}],
            tool_calls=[ToolCall(id="t1", name="calculator", input={"expression": "1+1"})],
        ),
        Message(role="tool", tool_call_id="t1", content="2", is_error=True),
        Message(
            role="assistant",
            provider="gemini",
            tool_calls=[ToolCall(id="t2", name="x")],
            raw=[{"role": "assistant", "content": None, "tool_calls": [{"id": "t2"}]}],
        ),
        Message(role="user", content="next"),  # t2 결과 없이 끊김
    ]
    msgs = to_openai_messages("sys", history, "gemini")
    # 다른 공급자 기록은 중립 형식으로 변환 (Claude thinking 블록은 보내지 않음)
    assert msgs[2]["tool_calls"][0]["function"]["arguments"] == '{"expression": "1+1"}'
    assert msgs[3]["content"].startswith("ERROR: ")
    assert msgs[4] == history[3].raw[0]  # 같은 공급자 원본은 그대로
    assert msgs[5]["role"] == "tool" and msgs[5]["tool_call_id"] == "t2"  # 끊긴 호출 보충
    assert msgs[6] == {"role": "user", "content": "next"}


def test_auto_select_gemini(monkeypatch):
    from app.agent import providers
    from app.config import settings

    providers.get_provider.cache_clear()
    monkeypatch.setattr(settings, "llm_provider", "")
    monkeypatch.setattr(settings, "gemini_api_key", "g-key")
    try:
        assert providers.get_provider().name == "gemini"
    finally:
        providers.get_provider.cache_clear()


def test_parallel_calls_same_index_gemini_style():
    """실제 Gemini 응답 형태: 병렬 호출 두 개가 같은 index=0, 다른 id로 온다 (운영에서 발견)."""
    turn = [
        chunk(
            {
                "tool_calls": [
                    {
                        "index": 0,
                        "id": "call_a",
                        "type": "function",
                        "function": {
                            "name": "calculator",
                            "arguments": '{"expression":"1234 * 5678 / 9"}',
                        },
                        "extra_content": SIG,
                    }
                ]
            }
        ),
        chunk(
            {
                "tool_calls": [
                    {
                        "index": 0,
                        "id": "call_b",
                        "type": "function",
                        "function": {
                            "name": "get_current_time",
                            "arguments": '{"timezone":"Asia/Seoul"}',
                        },
                    }
                ]
            }
        ),
        chunk(finish="tool_calls"),
    ]
    client = FakeClient([turn, FINAL_TURN])
    _, history, events = run(client, "계산하고 시각도")
    calls = [e.data for e in events if e.type == "tool_call"]
    assert [c["name"] for c in calls] == ["calculator", "get_current_time"]
    assert all(not e.data["is_error"] for e in events if e.type == "tool_result")
    sent = next(m for m in client.requests[1]["messages"] if m["role"] == "assistant")
    assert [c["id"] for c in sent["tool_calls"]] == ["call_a", "call_b"]
    assert sent["tool_calls"][0]["extra_content"] == SIG  # 서명은 첫 호출에만, 그대로


def test_parallel_calls_distinct_index_openai_style():
    turn = [
        chunk(
            {
                "tool_calls": [
                    {
                        "index": 0,
                        "id": "c1",
                        "type": "function",
                        "function": {"name": "calculator", "arguments": ""},
                    }
                ]
            }
        ),
        chunk(
            {
                "tool_calls": [
                    {
                        "index": 1,
                        "id": "c2",
                        "type": "function",
                        "function": {"name": "get_current_time", "arguments": ""},
                    }
                ]
            }
        ),
        chunk({"tool_calls": [{"index": 0, "function": {"arguments": '{"expression":"1+1"}'}}]}),
        chunk({"tool_calls": [{"index": 1, "function": {"arguments": "{}"}}]}),
        chunk(finish="tool_calls"),
    ]
    _, _, events = run(FakeClient([turn, FINAL_TURN]))
    calls = [e.data for e in events if e.type == "tool_call"]
    assert [(c["name"], c["input"]) for c in calls] == [
        ("calculator", {"expression": "1+1"}),
        ("get_current_time", {}),
    ]
