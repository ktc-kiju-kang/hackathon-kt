from collections.abc import AsyncIterator
from typing import Protocol

from app.agent.tools import Tool
from app.agent.types import Message, ProviderEvent


class LLMProvider(Protocol):
    """LLM 어댑터 인터페이스. 새 모델을 붙일 때 이것만 구현한다.

    stream_turn은 assistant 한 턴을 스트리밍한다: TextDelta를 0개 이상 내보낸 뒤
    마지막에 TurnComplete를 정확히 1번 내보낸다. 도구 실행은 하지 않는다 (loop.py 담당).
    """

    name: str

    def stream_turn(
        self, *, system: str, history: list[Message], tools: list[Tool]
    ) -> AsyncIterator[ProviderEvent]: ...
