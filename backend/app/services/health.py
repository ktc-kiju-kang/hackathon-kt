from datetime import UTC, datetime

from app.schemas.health import Health


def get_health() -> Health:
    return Health(status="ok", time=datetime.now(UTC))
