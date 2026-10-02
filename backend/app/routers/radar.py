from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.agent.providers import LLMProvider
from app.agent.stages import llm_provider
from app.core.quota import client_ip
from app.schemas.radar import Company, OpportunityRequest, RadarSnapshot
from app.services import radar as service
from app.services import snapshot

router = APIRouter(prefix="/radar", tags=["radar"])


@router.get("/companies", response_model=list[Company])
def list_companies() -> list[Company]:
    return service.get_companies()


@router.post("/opportunities")
def create_opportunities(
    body: OpportunityRequest,
    request: Request,
    provider: Annotated[LLMProvider, Depends(llm_provider)],
) -> StreamingResponse:
    """SSE: stage → opportunity × N → done (형식: docs/contracts/radar.md)"""
    stream = service.stream_opportunities(body, client_ip(request), provider)
    return StreamingResponse(
        stream,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/snapshot/{company_id}", response_model=RadarSnapshot)
def get_snapshot(company_id: str) -> RadarSnapshot:
    """데모 예비안: 미리 만든 결과 (LLM 호출 없음, 한도 미사용)"""
    return snapshot.get_radar_snapshot(company_id)
