from fastapi import APIRouter, Response

from app.schemas.dashboard import Dashboard, GithubStatus
from app.services import dashboard as service
from app.services import dashboard_github

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=Dashboard)
def dashboard(response: Response) -> Dashboard:
    response.headers["Cache-Control"] = "no-store"
    return service.get_dashboard()


@router.get("/github", response_model=GithubStatus)
def github(response: Response) -> GithubStatus:
    response.headers["Cache-Control"] = "no-store"  # 서버가 60초 캐시한다
    return dashboard_github.get_github_status()
