from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.agent.providers import LLMProvider
from app.agent.stages import llm_provider
from app.schemas.product import ProductRequest, ProductSnapshot
from app.services import product as service
from app.services import snapshot
from app.services.rate_limit import client_ip

router = APIRouter(prefix="/product", tags=["product"])


@router.post("/generate")
def generate(
    body: ProductRequest,
    request: Request,
    provider: Annotated[LLMProvider, Depends(llm_provider)],
) -> StreamingResponse:
    """SSE: stage(design) → stage(poc) → product → done (형식: docs/contracts/product.md)"""
    stream = service.stream_product(body, client_ip(request), provider)
    return StreamingResponse(
        stream,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/snapshot/{opportunity_id}", response_model=ProductSnapshot)
def get_snapshot(opportunity_id: str) -> ProductSnapshot:
    """데모 예비안: 미리 만든 결과 (LLM 호출 없음, 한도 미사용)"""
    return snapshot.get_product_snapshot(opportunity_id)
