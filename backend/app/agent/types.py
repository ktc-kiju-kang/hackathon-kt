"""공급자 중립 메시지·이벤트 타입. LLM을 바꿔도 대화 기록·저장 형식은 그대로다."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    id: str
    name: str
    input: dict[str, Any] = Field(default_factory=dict)


class Message(BaseModel):
    """대화 기록 한 칸.

    - user: content
    - assistant: content(텍스트) + tool_calls. raw는 같은 공급자로 이어갈 때 그대로 돌려줄
      공급자 원본 응답(Claude의 thinking 블록 등은 바꾸지 않고 다시 보내야 한다).
    - tool: tool_call_id + content(결과) + is_error
    """

    role: Literal["user", "assistant", "tool"]
    content: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_call_id: str | None = None
    is_error: bool = False
    provider: str | None = None
    raw: list[dict[str, Any]] | None = None


def close_orphan_tool_calls(history: list[Message]) -> list[Message]:
    """결과가 없는 tool_call에 '중단됨' 결과를 채운 사본을 돌려준다 (저장 기록은 바꾸지 않음).

    도구 실행 중 연결이 끊기거나 max_tokens로 끝나면 tool_call만 저장된다. 대부분의 LLM API는
    tool_call 뒤에 결과가 없으면 다음 요청을 거부하므로, 보낼 때만 보충한다.
    """
    out: list[Message] = []
    pending: list[str] = []

    def flush() -> None:
        out.extend(
            Message(role="tool", tool_call_id=i, content="중단됨: 결과 없음", is_error=True)
            for i in pending
        )
        pending.clear()

    for m in history:
        if m.role == "tool" and m.tool_call_id in pending:
            pending.remove(m.tool_call_id)
            out.append(m)
            continue
        flush()
        out.append(m)
        if m.role == "assistant":
            pending.extend(c.id for c in m.tool_calls)
    flush()
    return out


StopReason = Literal["end_turn", "tool_use", "max_tokens", "refusal", "error"]


# --- 공급자 → 루프 이벤트 ---
class TextDelta(BaseModel):
    type: Literal["text_delta"] = "text_delta"
    text: str


class TurnComplete(BaseModel):
    type: Literal["turn_complete"] = "turn_complete"
    message: Message  # 이번 턴의 assistant 메시지 (텍스트 + tool_calls + raw)
    stop_reason: StopReason
    usage: dict[str, int] = Field(default_factory=dict)


ProviderEvent = TextDelta | TurnComplete


# --- 루프 → 클라이언트(SSE) 이벤트. docs/contracts/chat.md 와 일치 ---
class AgentEvent(BaseModel):
    type: Literal["text", "tool_call", "tool_result", "message", "retry", "done", "error"]
    data: dict[str, Any] = Field(default_factory=dict)
