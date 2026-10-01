"""Claude 어댑터 (Anthropic Python SDK 1.x).

- 스트리밍 + 사용자 정의 도구 → eager_input_streaming 사용, 입력 검증은 loop.py(pydantic)가 한다.
- 거절(refusal) 시 서버가 다른 모델로 재시도하도록 fallbacks="default" 사용.
- thinking 블록은 같은 대화에서 그대로 돌려줘야 하므로 assistant 원본(raw)을 보관해 재전송한다.
"""

import logging
from collections.abc import AsyncIterator
from typing import Any

import anthropic

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

FALLBACK_BETA = "server-side-fallback-2026-07-01"
# 응답을 다시 보낼 때, 마지막 fallback 블록 앞의 이 타입들은 빼야 한다 (중간 거절 후 재시도 규칙)
_DROP_BEFORE_FALLBACK = {"thinking", "redacted_thinking", "tool_use", "server_tool_use"}


def _sanitize_raw(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    last_fb = max((i for i, b in enumerate(blocks) if b.get("type") == "fallback"), default=-1)
    if last_fb < 0:
        return blocks
    return [
        b
        for i, b in enumerate(blocks)
        if not (i < last_fb and b.get("type") in _DROP_BEFORE_FALLBACK)
    ]


def to_anthropic_messages(history: list[Message], provider_name: str) -> list[dict[str, Any]]:
    """중립 기록 → Anthropic messages. 연속된 tool 결과는 user 메시지 하나로 묶는다."""
    out: list[dict[str, Any]] = []
    for m in close_orphan_tool_calls(history):
        if m.role == "user":
            out.append({"role": "user", "content": m.content})
        elif m.role == "assistant":
            if m.raw is not None and m.provider == provider_name:
                content = m.raw  # thinking 블록 포함 원본 그대로
            else:
                content = ([{"type": "text", "text": m.content}] if m.content else []) + [
                    {"type": "tool_use", "id": c.id, "name": c.name, "input": c.input}
                    for c in m.tool_calls
                ]
            out.append({"role": "assistant", "content": content})
        else:  # tool
            block = {
                "type": "tool_result",
                "tool_use_id": m.tool_call_id,
                "content": m.content,
                "is_error": m.is_error,
            }
            if out and out[-1]["role"] == "user" and isinstance(out[-1]["content"], list):
                out[-1]["content"].append(block)
            else:
                out.append({"role": "user", "content": [block]})
    return out


def to_anthropic_tools(tools: list[Tool]) -> list[dict[str, Any]]:
    return [
        {
            "name": t.name,
            "description": t.description,
            "input_schema": t.input_model.model_json_schema(),
            "eager_input_streaming": True,
        }
        for t in tools
    ]


class AnthropicProvider:
    name = "anthropic"

    def __init__(self) -> None:
        # 키: settings(.env 포함) → 없으면 SDK 기본 자격증명 탐색(ANTHROPIC_API_KEY 등)
        self.client = anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key or None, max_retries=2
        )

    async def stream_turn(
        self, *, system: str, history: list[Message], tools: list[Tool]
    ) -> AsyncIterator[ProviderEvent]:
        params: dict[str, Any] = {
            "model": settings.llm_model,
            "max_tokens": settings.llm_max_tokens,
            "system": system,
            "messages": to_anthropic_messages(history, self.name),
            "output_config": {"effort": settings.llm_effort},
            "cache_control": {"type": "ephemeral"},  # system·tools·이전 대화 prefix 캐시
            "betas": [FALLBACK_BETA],
            "fallbacks": "default",
        }
        if tools:
            params["tools"] = to_anthropic_tools(tools)

        for attempt in range(3):
            emitted = False
            try:
                async with self.client.beta.messages.stream(**params) as stream:
                    async for event in stream:
                        if event.type == "text":
                            emitted = True
                            yield TextDelta(text=event.text)
                    final = await stream.get_final_message()
                break
            except ValueError:
                # 도구 입력 JSON을 아예 파싱 못 함 (tool_use 블록이 완성 전이라 답할 id가 없음)
                # → 같은 요청 재시도. 이미 화면에 텍스트를 보냈으면 중복되므로 재시도하지 않는다.
                # API 오류는 ValueError가 아니므로 그대로 올라간다.
                log.warning("unparseable tool input JSON (attempt %d)", attempt + 1)
                if emitted or attempt == 2:
                    raise

        # by_alias: fallback 블록의 `from` 필드가 파이썬에선 `from_` → API 형식으로 되돌린다
        raw = _sanitize_raw(
            [b.model_dump(mode="json", by_alias=True, exclude_none=True) for b in final.content]
        )
        # 텍스트·도구 호출은 재전송할 raw에서 뽑는다 (fallback 앞의 버려진 tool_use 제외)
        text = "".join(b.get("text", "") for b in raw if b.get("type") == "text")
        calls = [
            ToolCall(
                id=b["id"],
                name=b["name"],
                input=b["input"] if isinstance(b.get("input"), dict) else {},
            )
            for b in raw
            if b.get("type") == "tool_use"
        ]
        stop = final.stop_reason
        stop_reason = (
            stop
            if stop in ("end_turn", "tool_use", "max_tokens", "refusal")
            else ("tool_use" if calls else "end_turn")
        )
        yield TurnComplete(
            message=Message(
                role="assistant", content=text, tool_calls=calls, provider=self.name, raw=raw
            ),
            stop_reason=stop_reason,
            usage={
                "input_tokens": final.usage.input_tokens,
                "output_tokens": final.usage.output_tokens,
                "cache_read_input_tokens": final.usage.cache_read_input_tokens or 0,
            },
        )
