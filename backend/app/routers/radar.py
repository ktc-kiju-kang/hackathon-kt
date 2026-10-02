from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.schemas.radar import Company, OpportunityRequest
from app.services import radar as service

router = APIRouter(prefix="/radar", tags=["radar"])


def _ip(request: Request) -> str:
    # Render 프록시 뒤: 실제 클라이언트 IP는 X-Forwarded-For 첫 값
    fwd = request.headers.get("x-forwarded-for", "")
    return fwd.split(",")[0].strip() or (request.client.host if request.client else "unknown")


@router.get("/companies", response_model=list[Company])
def list_companies() -> list[Company]:
    return service.get_companies()


@router.post("/opportunities")
def create_opportunities(body: OpportunityRequest, request: Request) -> StreamingResponse:
    """SSE: stage → opportunity × N → done (형식: docs/contracts/radar.md)"""
    stream = service.stream_opportunities(body, _ip(request))
    return StreamingResponse(
        stream,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
