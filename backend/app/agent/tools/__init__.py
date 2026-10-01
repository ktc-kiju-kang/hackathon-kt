"""에이전트 도구 레지스트리. app/agent/tools/<name>.py 에 `tool = Tool(...)`을 두면 자동 등록된다.

입력은 pydantic 모델로 정의한다 → LLM에 보낼 JSON 스키마 생성 + 실행 전 검증을 동시에 한다.
도구 함수는 LLM이 만든 입력을 받으므로 '신뢰할 수 없는 입력'으로 다룬다.
"""

import importlib
import pkgutil
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from pydantic import BaseModel


@dataclass(frozen=True)
class Tool:
    name: str  # snake_case, 고유
    description: str  # LLM이 언제·어떻게 쓸지 판단하는 유일한 근거 — 구체적으로
    input_model: type[BaseModel]
    run: Callable[[Any], Awaitable[str]]  # input_model 인스턴스 → 결과 문자열 (JSON 권장)


@lru_cache
def get_tools() -> tuple[Tool, ...]:
    tools: list[Tool] = []
    for mod in sorted(pkgutil.iter_modules(__path__), key=lambda m: m.name):
        if mod.ispkg or mod.name.startswith("_"):
            continue
        module = importlib.import_module(f"{__name__}.{mod.name}")
        tool = getattr(module, "tool", None)
        if not isinstance(tool, Tool):
            raise RuntimeError(f"app/agent/tools/{mod.name}.py 에 `tool = Tool(...)`이 없습니다")
        tools.append(tool)
    names = [t.name for t in tools]
    if len(names) != len(set(names)):
        raise RuntimeError(f"도구 이름 중복: {names}")
    return tuple(tools)
