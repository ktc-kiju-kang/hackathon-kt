"""#21 계약 스키마: 계약 문서의 JSON 형태(from/in 별칭 포함)와 맞는지 확인."""

import pytest
from pydantic import ValidationError

from app.schemas.product import ProductCard, ProductRequest
from app.schemas.radar import Opportunity, OpportunityRequest

EVIDENCE = {
    "metric": "topic_share",
    "key": "Practical Guidance",
    "country": "KR",
    "from": "2024-07",
    "to": "2026-06",
    "from_value": 0.232,
    "to_value": 0.341,
    "change_pp": 10.9,
    "label": "KR 메시지 중 Practical Guidance 23.2% → 34.1% (2024-07 → 2026-06)",
}

OPPORTUNITY = {
    "id": "opp_1",
    "company_id": "kt-cloud",
    "country": "KR",
    "title": "Cloud 장애 대응 자동화",
    "trend": "업무용 실무 가이드 요청 증가",
    "target": ["KT Cloud 운영 조직"],
    "problem": "장애 시 로그를 사람이 직접 확인",
    "solution": "AI Agent가 원인과 조치안을 제안",
    "kt_assets": ["MSP 운영 조직"],
    "evidence": [EVIDENCE],
    "rationale": "실무 가이드 수요 증가가 운영 자동화 수요로 이어짐",
    "score": {"impact": 4, "feasibility": 3},
}


def test_opportunity_round_trips_with_alias():
    opp = Opportunity.model_validate(OPPORTUNITY)
    assert opp.model_dump(by_alias=True)["evidence"][0] == EVIDENCE


def test_opportunity_requires_evidence():
    with pytest.raises(ValidationError):
        Opportunity.model_validate({**OPPORTUNITY, "evidence": []})


def test_opportunity_request_defaults_and_limits():
    req = OpportunityRequest(company_id="kt")
    assert (req.country, req.count) == ("KR", 4)
    with pytest.raises(ValidationError):
        OpportunityRequest(company_id="kt", country="kr")
    with pytest.raises(ValidationError):
        OpportunityRequest(company_id="kt", count=6)


def test_product_card_aliases():
    card = ProductCard.model_validate(
        {
            "id": "prd_1",
            "opportunity_id": "opp_1",
            "name": "KT CloudOps Agent",
            "tagline": "장애 대응 자동화",
            "problem": "p",
            "target_users": [{"persona": "Cloud 운영자", "pain": "야간 장애"}],
            "value_props": ["MTTR 단축"],
            "features": [{"name": "로그 분석", "description": "d", "priority": "must"}],
            "user_flow": ["알림 수신", "분석", "조치안"],
            "data_needed": [{"name": "Runbook", "source": "운영팀", "availability": "internal"}],
            "apis": [{"method": "POST", "path": "/incidents", "description": "d"}],
            "architecture": {
                "components": [{"id": "a", "name": "Agent", "role": "분석"}],
                "edges": [{"from": "a", "to": "a"}],
            },
            "mvp_scope": {"in": ["분석"], "out": ["자동 조치"]},
            "poc_plan": {
                "duration_weeks": 3,
                "milestones": [{"week": 1, "goal": "데이터 연결"}],
                "success_metrics": ["정확도"],
                "risks": ["로그 접근 권한"],
            },
            "evidence": [EVIDENCE],
        }
    )
    dumped = card.model_dump(by_alias=True)
    assert dumped["mvp_scope"]["in"] == ["분석"]
    assert dumped["architecture"]["edges"][0]["from"] == "a"
    ProductRequest(opportunity=OPPORTUNITY)
