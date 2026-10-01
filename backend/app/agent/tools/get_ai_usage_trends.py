import asyncio
import json

from fastapi import HTTPException
from pydantic import BaseModel, Field

from app.agent.tools import Tool
from app.services import trends


class Input(BaseModel):
    country: str | None = Field(
        default="KR",
        pattern=r"^[A-Z]{2}$",
        description="ISO 2자리 대문자 국가 코드 (예: KR, US, JP). null이면 전 세계",
    )
    months: int = Field(
        default=12,
        ge=1,
        le=23,
        description="최신 월(2026-06)과 몇 개월 전을 비교할지. 23 = 전체 기간",
    )


async def run(args: Input) -> str:
    try:
        # 첫 호출은 CSV를 읽으므로 이벤트 루프를 막지 않게 스레드에서 실행한다
        summary = await asyncio.to_thread(trends.get_summary, args.country, args.months)
    except HTTPException as e:
        raise ValueError(e.detail) from None
    data = summary.model_dump(by_alias=True)
    data["source"] = "OpenAI Signals v2.0 (CC BY 4.0)"
    return json.dumps(data, ensure_ascii=False)


tool = Tool(
    name="get_ai_usage_trends",
    description=(
        "OpenAI Signals(개인 ChatGPT 사용 통계)에서 국가별 AI 활용 트렌드를 조회한다. "
        "주제별 메시지 비중(Writing, Practical Guidance, Technical help 등)과 "
        "업무 메시지 기준 비중, "
        "업무 관련 메시지 비중, 업무 메시지의 질문/작업 요청/표현 비중을 두 시점 비교로 돌려주고, "
        "국가면 인구 대비 사용량 순위도 준다. 값은 0~1 비중, change_pp는 %p 차이다. "
        "AI·ChatGPT 사용 트렌드나 국가 비교 질문, 사업 기회의 데이터 근거가 필요할 때 쓴다. "
        "기업(Enterprise) 계정은 포함되지 않는다."
    ),
    input_model=Input,
    run=run,
)
