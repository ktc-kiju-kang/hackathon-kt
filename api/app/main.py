from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import health

app = FastAPI(title="KT Hackathon API", docs_url="/api/docs", openapi_url="/api/openapi.json")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 모든 라우터는 /api 아래에 둔다 (web의 Vite 프록시와 맞춤)
app.include_router(health.router, prefix="/api", tags=["health"])
