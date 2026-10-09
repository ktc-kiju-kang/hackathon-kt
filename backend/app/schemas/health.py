# docs/contracts/health.md 와 1:1로 맞춘다. 변경 시 계약 문서 먼저 수정.
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Health(BaseModel):
    status: Literal["ok"]
    time: datetime
    version: str | None = None  # 배포된 git 커밋 SHA (로컬은 null)
    db: Literal["ok", "error", "unconfigured"] = "unconfigured"
    llm: str | None = None  # 에이전트 LLM 공급자 (anthropic | gemini | openai | mock)
    llm_mode: Literal["mock", "real"] | None = (
        None  # 실제 LLM을 부르는지 (공급자 설정 오류면 null)
    )
    client_ip: str | None = None  # 서버가 사용량 한도에 쓰는 요청자 IP (본인 IP만 보인다)
    uptime_seconds: int = Field(ge=0)  # 서버 프로세스 시작 후 지난 초 (재시작·콜드 스타트 확인용)
