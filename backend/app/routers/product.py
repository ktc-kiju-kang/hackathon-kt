from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.schemas.product import ProductRequest
from app.services import product as service
from app.services.rate_limit import client_ip

router = APIRouter(prefix="/product", tags=["product"])


@router.post("/generate")
def generate(body: ProductRequest, request: Request) -> StreamingResponse:
    """SSE: stage(design) → stage(poc) → product → done (형식: docs/contracts/product.md)"""
    stream = service.stream_product(body, client_ip(request))
    return StreamingResponse(
        stream,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
