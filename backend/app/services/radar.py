"""그룹사 + AI Opportunity Radar. 계약: docs/contracts/radar.md

단계: trend(트렌드 고르기) → match(사업 연결) → opportunity(기회 생성). 단계마다 LLM 1회 호출.
LLM은 근거를 서버가 준 후보 목록의 id로만 고르고, 숫자·문구는 trends.resolve_evidence가 채운다.
"""

import json
import uuid
from collections.abc import AsyncIterator
from functools import lru_cache
from pathlib import Path

from fastapi import HTTPException
from pydantic import BaseModel, Field

from app.agent.providers import LLMProvider
from app.agent.stages import StageRunner, stream_stages
from app.agent.structured import StructuredError
from app.schemas.radar import Company, Opportunity, OpportunityRequest, OpportunityScore
from app.schemas.trends import Evidence, EvidenceRef
from app.services import trends
from app.services.rate_limit import check_chat_quota

COMPANIES_FILE = Path(__file__).resolve().parents[2] / "data" / "companies.json"

SYSTEM = """\
당신은 KT 그룹의 AI 사업기획 분석가입니다. 한국어로 답합니다.
- 결과는 반드시 지정된 제출 도구를 한 번 호출해 제출합니다. 도구 밖에 결과를 쓰지 않습니다.
- 데이터 근거는 제공된 후보 목록의 id로만 고릅니다. 수치를 새로 만들거나 바꾸지 않습니다.
- 데이터는 개인 ChatGPT 사용 통계(OpenAI Signals)입니다. 기업 계정은 포함되지 않으므로,
  데이터가 직접 말하는 것(사용 패턴 변화)과 당신의 추론(사업 기회)을 구분합니다.
- 회사 정보는 공개 자료 요약입니다. 없는 사업·자산을 지어내지 않습니다.
- 고객 개인정보(개인별 결제·통화·위치 기록 등)를 그대로 활용하는 기회는 제안하지 않습니다.
  데이터가 필요하면 비식별·통계 데이터로 씁니다.
"""


# ---- 그룹사 ----


@lru_cache
def get_companies() -> list[Company]:
    return [Company.model_validate(c) for c in json.loads(COMPANIES_FILE.read_text("utf-8"))]


def get_company(company_id: str) -> Company:
    company = next((c for c in get_companies() if c.id == company_id), None)
    if company is None:
        raise HTTPException(status_code=404, detail="해당 그룹사가 없습니다")
    return company


# ---- LLM 단계별 출력 (제출 도구 입력) ----


class TrendPick(BaseModel):
    title: str = Field(description="트렌드 이름 (20자 안팎)")
    insight: str = Field(
        description="데이터가 보여주는 사용 패턴 변화와 이 회사에 주는 의미 (2문장)"
    )
    evidence_ids: list[str] = Field(min_length=1, max_length=4, description="근거 후보 id")


class TrendsOut(BaseModel):
    trends: list[TrendPick] = Field(min_length=2, max_length=4)


class Match(BaseModel):
    trend_title: str = Field(description="연결할 트렌드 title")
    business_area: str = Field(description="회사 business_areas 중 하나")
    kt_assets: list[str] = Field(default_factory=list, description="활용할 회사 assets 항목")
    angle: str = Field(description="트렌드와 사업이 만나는 지점 (1~2문장)")


class MatchesOut(BaseModel):
    matches: list[Match] = Field(min_length=2, max_length=6)


class OpportunityDraft(BaseModel):
    title: str = Field(description="사업 기회 이름 (예: Cloud 장애 대응 자동화)")
    trend: str = Field(description="근거가 된 트렌드 한 줄")
    target: list[str] = Field(min_length=1, max_length=4, description="대상 고객·조직")
    problem: str
    solution: str
    kt_assets: list[str] = Field(default_factory=list, description="활용할 회사 assets 항목")
    evidence_ids: list[str] = Field(min_length=1, max_length=4, description="근거 후보 id")
    rationale: str = Field(description="근거 데이터에서 이 기회로 이어지는 추론 (2~3문장)")
    impact: int = Field(ge=1, le=5)
    feasibility: int = Field(ge=1, le=5)


class OpportunitiesOut(BaseModel):
    opportunities: list[OpportunityDraft] = Field(min_length=1, max_length=5)


# ---- 근거 후보 ----


def _candidates(country: str) -> dict[str, Evidence]:
    """LLM에게 보여줄 근거 후보: 요청 국가와 전 세계의 모든 요약 지표 (id → Evidence)."""
    refs: list[EvidenceRef] = []
    for c in (country, None):
        s = trends.get_summary(c, trends.EVIDENCE_MONTHS)
        refs += [EvidenceRef(metric="topic_share", key=t.topic, country=c) for t in s.topics]
        refs += [
            EvidenceRef(metric="work_topic_share", key=t.topic, country=c) for t in s.work_topics
        ]
        refs += [EvidenceRef(metric="work_intent", key=i.intent, country=c) for i in s.work_intent]
        refs.append(EvidenceRef(metric="work_share", country=c))
        if s.usage_rank:
            refs.append(EvidenceRef(metric="usage_rank", country=c))
    resolved = trends.resolve_evidence(refs, {country, None})
    return {f"e{i + 1}": ev for i, ev in enumerate(resolved)}


def _candidate_lines(cands: dict[str, Evidence]) -> str:
    return "\n".join(f"- {i}: {ev.label}" for i, ev in cands.items())


def _pick(cands: dict[str, Evidence], ids: list[str]) -> list[Evidence]:
    seen: list[str] = []
    for i in ids:
        if i in cands and i not in seen:
            seen.append(i)
    return [cands[i] for i in seen]


# ---- 단계 실행 (mock이면 LLM 없이 고정 규칙) ----


def _company_text(company: Company, focus: str | None) -> str:
    data = company.model_dump(exclude={"sources"})
    text = f"회사 정보(공개 자료 요약):\n{json.dumps(data, ensure_ascii=False, indent=1)}"
    return text + (f"\n\n사용자가 관심 있는 방향: {focus}" if focus else "")


def _trend_prompt(company: Company, focus: str | None, cands: dict[str, Evidence]) -> str:
    return (
        f"{_company_text(company, focus)}\n\n근거 후보 (2024-07 → 2026-06):\n"
        f"{_candidate_lines(cands)}\n\n"
        "이 회사 사업과 관련이 큰 AI 활용 트렌드 2~4개를 고르세요. "
        "변화가 크고 회사 사업에 의미 있는 지표를 근거로 씁니다."
    )


def _match_prompt(company: Company, focus: str | None, picked: TrendsOut) -> str:
    return (
        f"{_company_text(company, focus)}\n\n고른 트렌드:\n"
        f"{json.dumps(picked.model_dump(), ensure_ascii=False, indent=1)}\n\n"
        "각 트렌드를 회사의 business_areas·assets와 연결하세요 (2~6건). "
        "business_area와 kt_assets는 회사 정보에 있는 문구 그대로 씁니다."
    )


def _opportunity_prompt(
    company: Company,
    focus: str | None,
    cands: dict[str, Evidence],
    picked: TrendsOut,
    matches: MatchesOut,
    count: int,
) -> str:
    return (
        f"{_company_text(company, focus)}\n\n근거 후보:\n{_candidate_lines(cands)}\n\n"
        f"고른 트렌드:\n{json.dumps(picked.model_dump(), ensure_ascii=False, indent=1)}\n\n"
        f"사업 연결:\n{json.dumps(matches.model_dump(), ensure_ascii=False, indent=1)}\n\n"
        f"이 회사가 만들 수 있는 AI 사업 기회 {count}개를 제안하세요. 서로 겹치지 않게, "
        "실제 고객과 문제가 분명하게, 각 항목은 1~2문장으로 짧게 씁니다. "
        "kt_assets는 회사 정보의 assets 문구 그대로, "
        "evidence_ids는 근거 후보 id로 씁니다. impact·feasibility는 1~5점입니다."
    )


def _to_opportunity(
    draft: OpportunityDraft, company: Company, country: str, cands: dict[str, Evidence]
) -> Opportunity | None:
    evidence = _pick(cands, draft.evidence_ids)
    if not evidence:
        return None
    return Opportunity(
        id=f"opp_{uuid.uuid4().hex[:12]}",
        company_id=company.id,
        country=country,
        title=draft.title,
        trend=draft.trend,
        target=draft.target,
        problem=draft.problem,
        solution=draft.solution,
        kt_assets=[a for a in draft.kt_assets if a in company.assets],
        evidence=evidence,
        rationale=draft.rationale,
        score=OpportunityScore(impact=draft.impact, feasibility=draft.feasibility),
    )


async def _run(req: OpportunityRequest, company: Company, runner: StageRunner) -> None:
    cands = _candidates(req.country)

    picked = await runner.run(
        "trend",
        tool_name="submit_trends",
        description="고른 AI 활용 트렌드를 제출한다.",
        output=TrendsOut,
        prompt=lambda: _trend_prompt(company, req.focus, cands),
        mock=lambda: _mock_trends(cands),
        summary=lambda out: " · ".join(t.title for t in out.trends),
    )

    def match_summary(out: MatchesOut) -> str:
        areas = sorted({m.business_area for m in out.matches})
        return f"{len(out.matches)}건 연결: {', '.join(areas)}"

    matches = await runner.run(
        "match",
        tool_name="submit_matches",
        description="트렌드와 회사 사업의 연결을 제출한다.",
        output=MatchesOut,
        prompt=lambda: _match_prompt(company, req.focus, picked),
        mock=lambda: _mock_matches(company, picked),
        summary=match_summary,
    )

    async def send_opportunities(out: OpportunitiesOut) -> str:
        # 기회 이벤트는 이 단계의 start와 done 사이에 보낸다 (계약). 하나도 없으면 done 대신 error.
        sent = 0
        for draft in out.opportunities[: req.count]:
            if (opp := _to_opportunity(draft, company, req.country, cands)) is not None:
                await runner.emit("opportunity", {"opportunity": opp.model_dump(by_alias=True)})
                sent += 1
        if sent == 0:
            raise StructuredError(
                "no_result", "데이터 근거가 있는 사업 기회를 찾지 못했어요. 다시 시도해 주세요."
            )
        return f"기회 {sent}건"

    await runner.run(
        "opportunity",
        tool_name="submit_opportunities",
        description="AI 사업 기회 목록을 제출한다.",
        output=OpportunitiesOut,
        prompt=lambda: _opportunity_prompt(company, req.focus, cands, picked, matches, req.count),
        mock=lambda: _mock_opportunities(company, picked, matches, req.count),
        summary=send_opportunities,
    )
    await runner.emit("done", {"stop_reason": "end", "usage": {}})


def stream_opportunities(
    req: OpportunityRequest, ip: str, provider: LLMProvider | None = None
) -> AsyncIterator[str]:
    """검증·한도 확인은 스트림 시작 전에 한다 (스트림 도중엔 상태코드를 바꿀 수 없음)."""
    company = get_company(req.company_id)
    trends.get_summary(req.country, trends.EVIDENCE_MONTHS)  # 지원하지 않는 국가면 404
    check_chat_quota(ip)
    return stream_stages(
        lambda runner: _run(req, company, runner), system=SYSTEM, provider=provider
    )


# ---- mock: 키 없이 UI 개발용 고정 결과 (실제 데이터 근거는 그대로 사용) ----


def _mock_trends(cands: dict[str, Evidence]) -> TrendsOut:
    # 요청 국가 지표 중 변화가 큰 3개 (후보는 항상 수십 개라 비지 않는다)
    own = [i for i, ev in cands.items() if ev.country is not None and ev.change_pp is not None]
    top = sorted(own, key=lambda i: abs(cands[i].change_pp or 0), reverse=True)[:3]
    return TrendsOut(
        trends=[
            TrendPick(title=f"[mock] 트렌드 {n + 1}", insight=cands[i].label, evidence_ids=[i])
            for n, i in enumerate(top)
        ]
    )


def _mock_matches(company: Company, picked: TrendsOut) -> MatchesOut:
    return MatchesOut(
        matches=[
            Match(
                trend_title=t.title,
                business_area=company.business_areas[n % len(company.business_areas)],
                kt_assets=company.assets[:1],
                angle=f"[mock] {t.title}을(를) {company.name} 사업에 연결",
            )
            for n, t in enumerate(picked.trends)
        ]
    )


_MOCK_KINDS = [
    "업무 자동화 에이전트",
    "고객 상담 AI",
    "데이터 분석 서비스",
    "AI 운영 도우미",
    "추천 서비스",
]


def _mock_opportunities(
    company: Company, picked: TrendsOut, matches: MatchesOut, count: int
) -> OpportunitiesOut:
    drafts = []
    for n in range(count):
        m = matches.matches[n % len(matches.matches)]
        t = picked.trends[n % len(picked.trends)]
        drafts.append(
            OpportunityDraft(
                title=f"[mock] {m.business_area} {_MOCK_KINDS[n % len(_MOCK_KINDS)]}",
                trend=t.insight,
                target=company.customers[:2],
                problem="[mock] 반복 업무와 문의 대응에 많은 인력이 든다.",
                solution="[mock] AI 에이전트가 데이터를 분석해 답변·조치안을 제안한다.",
                kt_assets=m.kt_assets,
                evidence_ids=t.evidence_ids,
                rationale="[mock] mock LLM이 만든 예시입니다. 실제 키를 설정하면 LLM이 추론합니다.",
                impact=4 - n % 2,
                feasibility=3 + n % 2,
            )
        )
    return OpportunitiesOut(opportunities=drafts)
