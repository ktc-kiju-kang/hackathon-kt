# docs/contracts/chat.md 와 1:1로 맞춘다. 변경 시 계약 문서 먼저 수정.
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=100)


class Conversation(BaseModel):
    id: str
    title: str | None
    created_at: datetime


class ChatMessageIn(BaseModel):
    content: str = Field(min_length=1, max_length=8000)


class ChatMessage(BaseModel):
    """화면 표시용 메시지 (공급자 원본 raw 제외)."""

    role: Literal["user", "assistant", "tool"]
    content: str
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    tool_call_id: str | None = None
    is_error: bool = False
    created_at: datetime | None = None
