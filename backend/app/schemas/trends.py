# docs/contracts/trends.md 와 1:1로 맞춘다. 변경 시 계약 문서 먼저 수정.
from typing import Literal

from pydantic import BaseModel, Field

Topic = Literal[
    "Writing",
    "Practical Guidance",
    "Seeking information",
    "Technical help",
    "Multimedia",
    "Self-expression",
    "Other/Unknown",
]
AskDoExpress = Literal["asking", "doing", "expressing"]
Month = str  # "YYYY-MM"
Dimension = Literal["topic", "work_related", "ask_do_express"]
EvidenceMetric = Literal[
    "topic_share", "work_topic_share", "work_share", "work_intent", "usage_rank"
]


class MonthRange(BaseModel):
    from_: Month = Field(alias="from")
    to: Month

    model_config = {"populate_by_name": True}


class Source(BaseModel):
    name: Literal["OpenAI Signals v2.0"] = "OpenAI Signals v2.0"
    license: Literal["CC BY 4.0"] = "CC BY 4.0"
    url: str


class TrendsMeta(BaseModel):
    months: MonthRange
    countries: list[str]
    topics: list[Topic]
    source: Source


class SeriesPoint(BaseModel):
    month: Month
    key: str
    share: float


class TrendSeries(BaseModel):
    dimension: Dimension
    country: str | None
    work_related: Literal[0, 1] | None
    points: list[SeriesPoint]


class TopicChange(BaseModel):
    topic: Topic
    from_share: float
    to_share: float
    change_pp: float


class WorkShare(BaseModel):
    from_: float = Field(alias="from")
    to: float
    change_pp: float

    model_config = {"populate_by_name": True}


class IntentChange(BaseModel):
    intent: AskDoExpress
    from_share: float
    to_share: float
    change_pp: float


class UsageRank(BaseModel):
    quarter: Month
    rank: int
    previous_quarter: Month | None
    previous_rank: int | None


class TrendSummary(BaseModel):
    country: str | None
    period: MonthRange
    topics: list[TopicChange]
    work_topics: list[TopicChange]
    work_share: WorkShare
    work_intent: list[IntentChange]
    usage_rank: UsageRank | None


class EvidenceRef(BaseModel):
    """LLM이 고르는 근거 지표. 숫자는 서버가 resolve_evidence로 채운다."""

    metric: EvidenceMetric
    key: str | None = None
    country: str | None = None


class Evidence(EvidenceRef):
    from_: Month = Field(alias="from")
    to: Month
    from_value: float | None
    to_value: float
    change_pp: float | None
    label: str

    model_config = {"populate_by_name": True}
