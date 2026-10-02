from fastapi import APIRouter, Request, Response

from app.core.quota import client_ip
from app.schemas.health import Health
from app.services import health as service

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=Health)
def health(request: Request, response: Response) -> Health:
    response.headers["Cache-Control"] = "no-store"  # client_ip가 요청자마다 다르다
    return service.get_health().model_copy(update={"client_ip": client_ip(request)})
