"""API 키 없이 동작하는 가짜 LLM. 로컬 개발·CI 테스트·프론트 작업용.

규칙: 마지막 메시지가 도구 결과면 그 결과로 답한다. 사용자 메시지가 시간·날짜 질문이면
get_current_time, 숫자 연산식이 있으면 calculator 도구를 부른다. 그 외엔 메아리.
"""

import re
import uuid
from collections.abc import AsyncIterator

from app.agent.tools import Tool
from app.agent.types import Message, ProviderEvent, TextDelta, ToolCall, TurnComplete

_EXPR = re.compile(r"[\d\s+\-*/().]{3,}")
_TIME = re.compile(r"시간|몇\s*시|요일|날짜|오늘|time", re.IGNORECASE)


class MockProvider:
    name = "mock"

    async def stream_turn(
        self, *, system: str, history: list[Message], tools: list[Tool]
    ) -> AsyncIterator[ProviderEvent]:
        names = {t.name for t in tools}
        last = history[-1]
        calls: list[ToolCall] = []
        if last.role == "tool":
            text = f"[mock] 도구 결과: {last.content}"
        else:
            q = last.content
            expr = _EXPR.search(q)
            if _TIME.search(q) and "get_current_time" in names:
                calls = [ToolCall(id=_id(), name="get_current_time", input={})]
            elif expr and any(op in expr.group() for op in "+-*/") and "calculator" in names:
                calls = [ToolCall(id=_id(), name="calculator", input={"expression": expr.group()})]
            text = "[mock] 도구를 호출합니다." if calls else f"[mock] {q}"

        for word in text.split(" "):
            yield TextDelta(text=word + " ")
        yield TurnComplete(
            message=Message(role="assistant", content=text, tool_calls=calls, provider=self.name),
            stop_reason="tool_use" if calls else "end_turn",
        )


def _id() -> str:
    return f"mock_{uuid.uuid4().hex[:12]}"
