"""단계형 LLM 생성 파이프라인 실행 (radar·product 공통).

계약: docs/contracts/radar.md "스트림 형식"

서비스는 단계를 선언만 한다 (이름·제출 도구·출력 모델·프롬프트·mock 결과·요약).
단계 시작/끝 이벤트, mock 폴백, 구조화 호출(`call_structured`), 요청당 호출 예산은 여기서 처리한다.
provider는 요청이 시작될 때 한 번 정해 모든 단계가 같은 것을 쓴다.
"""

from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from inspect import isawaitable
from typing import TypeVar

from pydantic import BaseModel

from app.agent.providers import LLMProvider, get_provider
from app.agent.structured import CallBudget, Emit, call_structured, sse_stream

T = TypeVar("T", bound=BaseModel)


def llm_provider() -> LLMProvider:
    """FastAPI 의존성: 요청이 쓸 LLM.

    테스트는 `app.dependency_overrides[llm_provider]`로 바꾼다.
    """
    return get_provider()


@dataclass
class StageRunner:
    """한 요청의 단계 실행기. 단계 사이에서 `emit`으로 단계 밖 이벤트(결과 등)를 보낼 수 있다."""

    emit: Emit
    budget: CallBudget
    provider: LLMProvider
    system: str

    async def run(
        self,
        name: str,
        *,
        tool_name: str,
        description: str,
        output: type[T],
        prompt: Callable[[], str],
        mock: Callable[[], T],
        summary: Callable[[T], str | Awaitable[str]],
    ) -> T:
        """단계 하나를 실행한다: start → (mock | LLM) → summary → done.

        - provider가 mock이면 LLM을 부르지 않고 `mock()` 결과를 쓴다 (`prompt`는 만들지도 않는다).
        - `summary`는 done 직전에 실행된다. 이 단계의 결과 이벤트(예: opportunity)를 보내거나
          결과가 비면 StructuredError를 던지는 후처리를 둘 수 있다. 던지면 done은 안 나간다.
        - 실패하면 StructuredError(code=bad_output | limit | rate_limit | ...)를 던진다.
        """
        await self.emit("stage", {"stage": name, "status": "start"})
        if self.provider.name == "mock":
            out = mock()
        else:
            out = await call_structured(
                system=self.system,
                prompt=prompt(),
                tool_name=tool_name,
                description=description,
                model=output,
                emit=self.emit,
                budget=self.budget,
                provider=self.provider,
            )
        text = summary(out)
        if isawaitable(text):
            text = await text
        await self.emit("stage", {"stage": name, "status": "done", "summary": text})
        return out


def stream_stages(
    run: Callable[[StageRunner], Awaitable[None]],
    *,
    system: str,
    max_calls: int | None = None,
    provider: LLMProvider | None = None,
) -> AsyncIterator[str]:
    """`run(runner)`가 보내는 이벤트를 SSE 문자열로 스트리밍한다 (`sse_stream` 사용).

    검증·한도 확인은 이 함수를 부르기 전에 끝낸다 (스트림 도중엔 상태코드를 바꿀 수 없음).
    `max_calls`는 요청당 LLM 호출 상한(없으면 AGENT_MAX_TURNS).
    `provider`가 없으면 설정에서 고른다.
    """
    chosen = provider or get_provider()
    return sse_stream(lambda emit: run(StageRunner(emit, CallBudget(max_calls), chosen, system)))
