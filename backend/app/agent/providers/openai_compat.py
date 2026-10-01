"""OpenAI 호환 Chat Completions 어댑터. Gemini가 기본 프리셋이며 Groq·GitHub Models·OpenRouter·
Ollama 등 OpenAI 호환 API는 LLM_BASE_URL·LLM_MODEL·LLM_API_KEY만 바꿔 같은 코드로 쓴다.

- assistant 응답 원본(tool_calls의 알 수 없는 필드 포함)을 raw로 보관해 그대로 재전송한다.
  Gemini 3는 도구 호출에 thought signature를 붙여 주고 다음 요청에 돌려받아야 하는데,
  필드 위치를 가정하지 않고 받은 그대로 돌려주는 방식으로 처리한다.
"""

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI

from app.agent.tools import Tool
from app.agent.types import (
    Message,
    ProviderEvent,
    TextDelta,
    ToolCall,
    TurnComplete,
    close_orphan_tool_calls,
)
from app.config import settings

log = logging.getLogger(__name__)

PRESETS: dict[str, dict[str, Any]] = {
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "model": "gemini-3.8-flash",
        "reasoning_effort": True,  # Gemini는 OpenAI reasoning_effort를 thinking 수준으로 매핑
    },
    "openai": {"base_url": None, "model": "", "reasoning_effort": False},
}

_STOP = {"stop": "end_turn", "tool_calls": "tool_use", "length": "max_tokens"}


def _strip_titles(schema: Any) -> Any:
    """pydantic 스키마의 title 키 제거 (일부 호환 API가 JSON Schema 부분집합만 받는다)."""
    if isinstance(schema, dict):
        return {k: _strip_titles(v) for k, v in schema.items() if k != "title"}
    if isinstance(schema, list):
        return [_strip_titles(v) for v in schema]
    return schema


def to_openai_tools(tools: list[Tool]) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": _strip_titles(t.input_model.model_json_schema()),
            },
        }
        for t in tools
    ]


def to_openai_messages(system: str, history: list[Message], provider_name: str) -> list[dict]:
    out: list[dict[str, Any]] = [{"role": "system", "content": system}]
    for m in close_orphan_tool_calls(history):
        if m.role == "user":
            out.append({"role": "user", "content": m.content})
        elif m.role == "assistant":
            if m.raw and m.provider == provider_name:
                out.append(m.raw[0])  # 받은 그대로 (thought signature 등 보존)
                continue
            msg: dict[str, Any] = {"role": "assistant", "content": m.content or None}
            if m.tool_calls:
                msg["tool_calls"] = [
                    {
                        "id": c.id,
                        "type": "function",
                        "function": {"name": c.name, "arguments": json.dumps(c.input)},
                    }
                    for c in m.tool_calls
                ]
            out.append(msg)
        else:
            content = f"ERROR: {m.content}" if m.is_error else m.content
            out.append({"role": "tool", "tool_call_id": m.tool_call_id, "content": content})
    return out


def _merge_tool_delta(acc: dict[int, dict[str, Any]], delta: dict[str, Any]) -> None:
    """스트리밍 tool_call 조각을 index별로 합친다. 알 수 없는 필드도 보존한다."""
    slot = acc.setdefault(delta.get("index", 0), {"type": "function", "function": {}})
    for k, v in delta.items():
        if k == "index":
            continue
        if k == "function":
            fn = slot["function"]
            if v.get("name"):
                # 보통 첫 조각에 이름 전체가 온다. 이름이 쪼개져 오는 API면 이어 붙인다
                if "name" not in fn:
                    fn["name"] = v["name"]
                elif fn["name"] != v["name"]:
                    fn["name"] += v["name"]
            if v.get("arguments"):
                fn["arguments"] = fn.get("arguments", "") + v["arguments"]
            for fk, fv in v.items():
                if fk not in ("name", "arguments"):
                    fn[fk] = fv
        else:
            slot[k] = v


class OpenAICompatProvider:
    def __init__(self, preset: str = "gemini", client: AsyncOpenAI | None = None) -> None:
        self.name = preset
        cfg = PRESETS[preset]
        self.model = settings.llm_model or cfg["model"]
        if not self.model:
            raise ValueError("LLM_MODEL을 설정하세요")
        self.use_reasoning_effort = cfg["reasoning_effort"]
        api_key = settings.gemini_api_key if preset == "gemini" else settings.llm_api_key
        self.client = client or AsyncOpenAI(
            api_key=api_key or settings.llm_api_key or "missing",
            base_url=settings.llm_base_url or cfg["base_url"],
            max_retries=2,
        )

    async def stream_turn(
        self, *, system: str, history: list[Message], tools: list[Tool]
    ) -> AsyncIterator[ProviderEvent]:
        params: dict[str, Any] = {
            "model": self.model,
            "messages": to_openai_messages(system, history, self.name),
            "max_tokens": settings.llm_max_tokens,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if tools:
            params["tools"] = to_openai_tools(tools)
        if self.use_reasoning_effort and settings.llm_effort in ("low", "medium", "high"):
            params["reasoning_effort"] = settings.llm_effort

        text_parts: list[str] = []
        calls: dict[int, dict[str, Any]] = {}
        finish: str | None = None
        usage: dict[str, int] = {}
        stream = await self.client.chat.completions.create(**params)
        async for chunk in stream:
            if chunk.usage:
                usage = {
                    "input_tokens": chunk.usage.prompt_tokens or 0,
                    "output_tokens": chunk.usage.completion_tokens or 0,
                }
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            delta = choice.delta
            if delta.content:
                text_parts.append(delta.content)
                yield TextDelta(text=delta.content)
            for tc in delta.tool_calls or []:
                _merge_tool_delta(calls, tc.model_dump(exclude_none=True))
            if choice.finish_reason:
                finish = choice.finish_reason

        text = "".join(text_parts)
        raw_calls = [calls[i] for i in sorted(calls)]
        tool_calls = []
        for i, c in enumerate(raw_calls):
            c.setdefault("id", f"call_{i}")
            args = c["function"].get("arguments") or "{}"
            try:
                parsed = json.loads(args)
            except json.JSONDecodeError:
                log.warning("invalid tool arguments JSON from %s: %r", self.name, args[:200])
                parsed = None
            # 파싱 실패는 검증에서 걸리도록 dict가 아닌 표시값을 넣는다 (기본값으로 실행되지 않게)
            tool_calls.append(
                ToolCall(
                    id=c["id"],
                    name=c["function"].get("name", ""),
                    input=parsed if isinstance(parsed, dict) else {"__invalid_json__": args},
                )
            )

        raw_msg: dict[str, Any] = {"role": "assistant", "content": text or None}
        if raw_calls:
            raw_msg["tool_calls"] = raw_calls
        stop = _STOP.get(finish or "", "tool_use" if tool_calls else "end_turn")
        if finish == "content_filter":
            stop = "refusal"
        yield TurnComplete(
            message=Message(
                role="assistant",
                content=text,
                tool_calls=tool_calls,
                provider=self.name,
                raw=[raw_msg],
            ),
            stop_reason=stop,
            usage=usage,
        )
