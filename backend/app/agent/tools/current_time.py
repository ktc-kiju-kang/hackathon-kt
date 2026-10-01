import json
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field

from app.agent.tools import Tool


class Input(BaseModel):
    timezone: str = Field(default="Asia/Seoul", description="IANA 타임존 (예: Asia/Seoul, UTC)")


async def run(args: Input) -> str:
    try:
        now = datetime.now(ZoneInfo(args.timezone))
    except ZoneInfoNotFoundError:
        raise ValueError(f"알 수 없는 타임존: {args.timezone}") from None
    return json.dumps({"timezone": args.timezone, "now": now.isoformat()}, ensure_ascii=False)


tool = Tool(
    name="get_current_time",
    description="현재 날짜와 시각을 조회한다. '오늘', '지금', 요일·날짜 계산이 필요할 때 사용.",
    input_model=Input,
    run=run,
)
