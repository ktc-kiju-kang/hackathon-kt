from datetime import UTC, datetime

from app.config import settings
from app.schemas.health import Health


def get_health() -> Health:
    return Health(status="ok", time=datetime.now(UTC), version=settings.render_git_commit or None)
