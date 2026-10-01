from fastapi import APIRouter

from app.schemas.health import Health
from app.services import health as service

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=Health)
def health() -> Health:
    return service.get_health()
