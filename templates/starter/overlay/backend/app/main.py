from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.db import init_db
from app.routers import discover_routers


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()  # 마이그레이션을 서버 시작 시 적용 — 파일 이름·SQL 오류면 서버가 뜨지 않는다
    yield


app = FastAPI(
    title="Hackathon API", docs_url="/api/docs", openapi_url="/api/openapi.json", lifespan=lifespan
)

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
