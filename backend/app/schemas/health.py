# docs/contracts/health.md 와 1:1로 맞춘다. 변경 시 계약 문서 먼저 수정.
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class Health(BaseModel):
    status: Literal["ok"]
    time: datetime
    version: str | None = None  # 배포된 git 커밋 SHA (로컬은 null)
    db: Literal["ok", "error", "unconfigured"] = "unconfigured"
    llm: str | None = None  # 에이전트 LLM 공급자 (anthropic | gemini | openai | mock)
    client_ip: str | None = None  # 서버가 사용량 한도에 쓰는 요청자 IP (본인 IP만 보인다)
