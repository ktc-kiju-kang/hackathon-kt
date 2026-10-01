# docs/contracts/product.md 와 1:1로 맞춘다. 변경 시 계약 문서 먼저 수정.
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.radar import Opportunity
from app.schemas.trends import Evidence


class ProductRequest(BaseModel):
    opportunity: Opportunity
    notes: str | None = Field(default=None, max_length=500)


class TargetUser(BaseModel):
    persona: str
    pain: str


class Feature(BaseModel):
    name: str
    description: str
    priority: Literal["must", "should", "could"]


class DataNeed(BaseModel):
    name: str
    source: str
    availability: Literal["public", "internal", "to_collect"]


class ApiSpec(BaseModel):
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    path: str
    description: str


class Component(BaseModel):
    id: str
    name: str
    role: str


class Edge(BaseModel):
    from_: str = Field(alias="from")
    to: str
    label: str | None = None

    model_config = {"populate_by_name": True}


class Architecture(BaseModel):
    components: list[Component]
    edges: list[Edge]


class MvpScope(BaseModel):
    in_: list[str] = Field(alias="in")
    out: list[str]

    model_config = {"populate_by_name": True}


class Milestone(BaseModel):
    week: int
    goal: str


class PocPlan(BaseModel):
    duration_weeks: int = Field(ge=1, le=12)
    milestones: list[Milestone]
    success_metrics: list[str]
    risks: list[str]


class ProductCard(BaseModel):
    id: str
    opportunity_id: str
    name: str
    tagline: str
    problem: str
    target_users: list[TargetUser]
    value_props: list[str]
    features: list[Feature]
    user_flow: list[str]
    data_needed: list[DataNeed]
    apis: list[ApiSpec]
    architecture: Architecture
    mvp_scope: MvpScope
    poc_plan: PocPlan
    evidence: list[Evidence]
