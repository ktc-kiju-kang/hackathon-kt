from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.schemas.product import ProductRequest
from app.services import product as service

router = APIRouter(prefix="/product", tags=["product"])


def _ip(request: Request) -> str:
    # Render 프록시 뒤: 실제 클라이언트 IP는 X-Forwarded-For 첫 값
    fwd = request.headers.get("x-forwarded-for", "")
    return fwd.split(",")[0].strip() or (request.client.host if request.client else "unknown")


@router.post("/generate")
def generate(body: ProductRequest, request: Request) -> StreamingResponse:
    """SSE: stage(design) → stage(poc) → product → done (형식: docs/contracts/product.md)"""
    stream = service.stream_product(body, _ip(request))
    return StreamingResponse(
        stream,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
