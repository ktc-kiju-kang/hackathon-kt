"""도구 호출 루프. 공급자(LLM)와 무관하게 동작한다.

run_agent(history)는 이벤트를 스트리밍하며 새 메시지(assistant/tool)를 history에 덧붙인다.
history는 append-only — 앞선 메시지를 고치지 않는다 (Claude thinking 블록 유효성 유지).
"""

import asyncio
import json
import logging
from collections.abc import AsyncIterator

from pydantic import ValidationError

from app.agent.errors import classify
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.providers import LLMProvider, get_provider
from app.agent.tools import Tool, get_tools
from app.agent.types import AgentEvent, Message, TextDelta, ToolCall, TurnComplete
from app.core.config import settings

log = logging.getLogger(__name__)


async def _run_tool(tools: dict[str, Tool], call: ToolCall) -> Message:
    tool = tools.get(call.name)
    if tool is None:
        return _tool_msg(call, f"알 수 없는 도구: {call.name}", error=True)
    if "__invalid_json__" in call.input:  # 어댑터가 JSON 파싱 실패를 표시한 경우
        payload = {"INVALID_JSON": call.input["__invalid_json__"]}
        return _tool_msg(call, json.dumps(payload, ensure_ascii=False), error=True)
    try:
        args = tool.input_model.model_validate(call.input)  # LLM 입력은 항상 검증 후 실행
    except ValidationError as e:
        payload = {"INVALID_INPUT": call.input, "errors": e.errors(include_url=False)}
        return _tool_msg(call, json.dumps(payload, ensure_ascii=False, default=str), error=True)
    try:
        result = await asyncio.wait_for(tool.run(args), timeout=settings.agent_tool_timeout)
        return _tool_msg(call, result)
    except Exception as e:  # 도구 오류는 LLM에게 돌려줘서 스스로 고치게 한다
        log.warning("tool %s failed: %s", call.name, e)
        return _tool_msg(call, f"{type(e).__name__}: {e}", error=True)


def _tool_msg(call: ToolCall, content: str, error: bool = False) -> Message:
    return Message(role="tool", tool_call_id=call.id, content=content, is_error=error)


async def run_agent(
    history: list[Message],
    *,
    provider: LLMProvider | None = None,
    tools: tuple[Tool, ...] | None = None,
    system: str = SYSTEM_PROMPT,
) -> AsyncIterator[AgentEvent]:
    provider = provider or get_provider()
    tools = get_tools() if tools is None else tools
    by_name = {t.name: t for t in tools}

    for _ in range(settings.agent_max_turns):
        turn: TurnComplete | None = None
        for attempt in range(settings.agent_llm_retries + 1):
            emitted = False
            try:
                async for ev in provider.stream_turn(
                    system=system, history=history, tools=list(tools)
                ):
                    if isinstance(ev, TextDelta):
                        emitted = True
                        yield AgentEvent(type="text", data={"text": ev.text})
                    else:
                        turn = ev
                break
            except Exception as e:
                err = classify(e)
                log.warning("LLM call failed (%s, attempt %d): %r", err.code, attempt + 1, e)
                # 이미 글자를 내보냈으면 다시 시도하면 중복되므로 멈춘다
                if err.retryable and not emitted and attempt < settings.agent_llm_retries:
                    wait = min(
                        err.retry_after or settings.agent_retry_delay * (2**attempt),
                        settings.agent_retry_max_delay,
                    )
                    yield AgentEvent(
                        type="retry",
                        data={"code": err.code, "wait_seconds": wait, "attempt": attempt + 1},
                    )
                    await asyncio.sleep(wait)
                    continue
                yield AgentEvent(type="error", data={"code": err.code, "message": err.message})
                return
        if turn is None:
            yield AgentEvent(type="error", data={"message": "LLM이 턴을 끝내지 않았습니다"})
            return

        history.append(turn.message)
        yield AgentEvent(type="message", data={"message": turn.message.model_dump(exclude={"raw"})})

        if turn.stop_reason == "refusal":
            yield AgentEvent(type="error", data={"message": "모델이 요청을 거절했습니다"})
            return
        if not turn.message.tool_calls:
            yield AgentEvent(
                type="done", data={"stop_reason": turn.stop_reason, "usage": turn.usage}
            )
            return
        if turn.stop_reason == "max_tokens":
            # 잘린 도구 입력은 그럴듯한 부분 객체로 파싱될 수 있다 → 실행하지 않는다
            yield AgentEvent(type="error", data={"message": "응답이 길이 제한에 걸려 잘렸습니다"})
            return

        for call in turn.message.tool_calls:
            yield AgentEvent(type="tool_call", data=call.model_dump())
        # 여러 도구는 동시에 실행하고, 결과는 모두 모아 한 번에 돌려준다
        results = await asyncio.gather(*(_run_tool(by_name, c) for c in turn.message.tool_calls))
        for msg in results:
            history.append(msg)
            yield AgentEvent(
                type="tool_result",
                data={
                    "tool_call_id": msg.tool_call_id,
                    "content": msg.content,
                    "is_error": msg.is_error,
                },
            )

    yield AgentEvent(
        type="error", data={"message": f"최대 {settings.agent_max_turns}턴을 넘었습니다"}
    )
