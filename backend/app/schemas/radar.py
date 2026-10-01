# docs/contracts/radar.md 와 1:1로 맞춘다. 변경 시 계약 문서 먼저 수정.
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.trends import Evidence

Score = Literal[1, 2, 3, 4, 5]


class Company(BaseModel):
    id: str
    name: str
    name_en: str
    summary: str
    business_areas: list[str]
    customers: list[str]
    assets: list[str]
    sources: list[str]


class OpportunityRequest(BaseModel):
    company_id: str
    country: str = Field(default="KR", pattern=r"^[A-Z]{2}$")
    focus: str | None = Field(default=None, max_length=200)
    count: int = Field(default=4, ge=3, le=5)


class OpportunityScore(BaseModel):
    impact: Score
    feasibility: Score


class Opportunity(BaseModel):
    id: str
    company_id: str
    country: str
    title: str
    trend: str
    target: list[str]
    problem: str
    solution: str
    kt_assets: list[str]
    evidence: list[Evidence] = Field(min_length=1)
    rationale: str
    score: OpportunityScore
