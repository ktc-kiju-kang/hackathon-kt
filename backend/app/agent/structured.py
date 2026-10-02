"""구조화 출력 + 단계형 SSE 헬퍼 (radar·product 공통). 계약: docs/contracts/radar.md

LLMProvider에는 structured output API가 없으므로, 결과 제출용 도구 하나만 넘겨 호출하게 하고
그 도구 입력(pydantic)을 결과로 쓴다. 대화 기록을 남기지 않는 단발 호출이다.
"""

import asyncio
import json
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from app.agent.errors import classify
from app.agent.providers import LLMProvider, get_provider
from app.agent.tools import Tool
from app.agent.types import Message, TurnComplete
from app.config import settings

log = logging.getLogger(__name__)

PING_INTERVAL = 15.0
OUTPUT_ATTEMPTS = 2  # 도구를 안 부르거나 형식이 틀리면 1회 다시 요청 (계약: bad_output)

Emit = Callable[[str, dict[str, Any]], Awaitable[None]]
T = TypeVar("T", bound=BaseModel)


class StructuredError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


async def _unused(_: BaseModel) -> str:  # 제출 도구는 실행하지 않는다
    raise RuntimeError("submit tool is not executed")


def _inline_refs(schema: dict[str, Any]) -> dict[str, Any]:
    """$defs/$ref를 펼친다. 일부 공급자(Gemini 등)는 도구 스키마의 $ref를 지원하지 않는다."""
    defs = schema.get("$defs", {})

    def walk(node: Any) -> Any:
        if isinstance(node, dict):
            if "$ref" in node:
                return walk(defs[node["$ref"].rsplit("/", 1)[-1]])
            return {k: walk(v) for k, v in node.items() if k != "$defs"}
        if isinstance(node, list):
            return [walk(v) for v in node]
        return node

    return walk(schema)


def _submit_model(model: type[T]) -> type[T]:
    schema = _inline_refs(model.model_json_schema())

    class Submit(model):  # type: ignore[valid-type, misc]
        @classmethod
        def model_json_schema(cls, *args: Any, **kwargs: Any) -> dict[str, Any]:
            return schema

    return Submit


async def call_structured(
    *,
    system: str,
    prompt: str,
    tool_name: str,
    description: str,
    model: type[T],
    emit: Emit,
    provider: LLMProvider | None = None,
) -> T:
    """LLM에게 `tool_name` 도구를 한 번 호출하게 해 그 입력을 `model`로 검증해 돌려준다.

    일시 오류(429·5xx)는 대기 후 재시도하며 `retry` 이벤트를 emit한다.
    실패하면 StructuredError(code=bad_output | rate_limit | ...)를 던진다.
    """
    provider = provider or get_provider()
    tool = Tool(
        name=tool_name, description=description, input_model=_submit_model(model), run=_unused
    )
    history = [Message(role="user", content=prompt)]

    for _ in range(OUTPUT_ATTEMPTS):
        turn = await _one_turn(provider, system, history, tool, emit)
        for call in turn.message.tool_calls:
            if call.name != tool_name:
                continue
            try:
                return model.model_validate(call.input)
            except ValidationError as e:
                log.warning("%s invalid output: %s", tool_name, e.errors(include_url=False)[:3])
    raise StructuredError("bad_output", "AI가 결과 형식을 맞추지 못했어요. 다시 시도해 주세요.")


async def _one_turn(
    provider: LLMProvider, system: str, history: list[Message], tool: Tool, emit: Emit
) -> TurnComplete:
    for attempt in range(settings.agent_llm_retries + 1):
        try:
            turn: TurnComplete | None = None
            async for ev in provider.stream_turn(system=system, history=history, tools=[tool]):
                if isinstance(ev, TurnComplete):
                    turn = ev
            if turn is None:
                raise StructuredError(
                    "internal", "AI가 응답을 끝내지 않았어요. 다시 시도해 주세요."
                )
            return turn
        except StructuredError:
            raise
        except Exception as e:
            err = classify(e)
            log.warning("LLM call failed (%s, attempt %d): %r", err.code, attempt + 1, e)
            if err.retryable and attempt < settings.agent_llm_retries:
                wait = min(
                    err.retry_after or settings.agent_retry_delay * (2**attempt),
                    settings.agent_retry_max_delay,
                )
                await emit(
                    "retry", {"code": err.code, "wait_seconds": wait, "attempt": attempt + 1}
                )
                await asyncio.sleep(wait)
                continue
            raise StructuredError(err.code, err.message) from e
    raise AssertionError("unreachable")


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


def sse_stream(run: Callable[[Emit], Awaitable[None]]) -> AsyncIterator[str]:
    """`run(emit)`이 보내는 이벤트를 SSE 문자열로 스트리밍한다.

    - 15초마다 `: ping` (생성이 오래 걸려도 연결 유지)
    - run이 StructuredError를 던지면 `error` 이벤트로 끝낸다. 그 외 예외는 `internal`
    - 클라이언트가 끊으면 run을 취소한다 (LLM 비용 절약)
    """

    async def events() -> AsyncIterator[str]:
        queue: asyncio.Queue[str | None] = asyncio.Queue()

        async def emit(event: str, data: dict[str, Any]) -> None:
            await queue.put(_sse(event, data))

        async def produce() -> None:
            try:
                await run(emit)
            except StructuredError as e:
                await emit("error", {"code": e.code, "message": e.message})
            except Exception:
                log.exception("structured stream failed")
                await emit("error", {"code": "internal", "message": "생성 중 오류가 났어요."})
            finally:
                await queue.put(None)

        task = asyncio.create_task(produce())
        try:
            while True:
                try:
                    chunk = await asyncio.wait_for(queue.get(), timeout=PING_INTERVAL)
                except TimeoutError:
                    yield ": ping\n\n"
                    continue
                if chunk is None:
                    break
                yield chunk
        finally:
            task.cancel()

    return events()
