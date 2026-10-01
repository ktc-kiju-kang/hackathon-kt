from fastapi import APIRouter, Query

from app.schemas.trends import Dimension, TrendSeries, TrendsMeta, TrendSummary
from app.services import trends as service

router = APIRouter(prefix="/trends", tags=["trends"])

CountryQuery = Query(default=None, pattern=r"^[A-Z]{2}$", description="생략하면 전 세계")
MonthQuery = r"^\d{4}-\d{2}$"


@router.get("/meta", response_model=TrendsMeta)
def get_meta() -> TrendsMeta:
    return service.get_meta()


@router.get("/series", response_model=TrendSeries)
def get_series(
    dimension: Dimension,
    country: str | None = CountryQuery,
    work_related: int | None = Query(default=None, ge=0, le=1),
    from_: str | None = Query(default=None, alias="from", pattern=MonthQuery),
    to: str | None = Query(default=None, pattern=MonthQuery),
) -> TrendSeries:
    return service.get_series(dimension, country, work_related, from_, to)


@router.get("/summary", response_model=TrendSummary)
def get_summary(
    country: str | None = CountryQuery, months: int = Query(default=12, ge=1, le=23)
) -> TrendSummary:
    return service.get_summary(country, months)
