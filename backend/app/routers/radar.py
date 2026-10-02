from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.schemas.radar import Company, OpportunityRequest
from app.services import radar as service
from app.services.rate_limit import client_ip

router = APIRouter(prefix="/radar", tags=["radar"])


@router.get("/companies", response_model=list[Company])
def list_companies() -> list[Company]:
    return service.get_companies()


@router.post("/opportunities")
def create_opportunities(body: OpportunityRequest, request: Request) -> StreamingResponse:
    """SSE: stage → opportunity × N → done (형식: docs/contracts/radar.md)"""
    stream = service.stream_opportunities(body, client_ip(request))
    return StreamingResponse(
        stream,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
