from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import discover_routers

app = FastAPI(title="KT Hackathon API", docs_url="/api/docs", openapi_url="/api/openapi.json")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=settings.cors_origin_regex or None,
    allow_methods=["*"],
    allow_headers=["*"],
)

# app/routers/<feature>.py 의 router를 자동 등록. 모든 경로는 /api 아래.
for router in discover_routers():
    app.include_router(router, prefix="/api")
