"""Supabase 클라이언트. 서비스 레이어(app/services/*)에서만 사용한다.

예: rows = get_supabase().table("items").select("*").execute().data
"""

from functools import lru_cache

from supabase import Client, ClientOptions, create_client

from app.core.config import settings


@lru_cache
def get_supabase() -> Client:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY 환경변수가 필요합니다")
    return create_client(
        settings.supabase_url,
        settings.supabase_service_role_key,
        # 서버용: 세션 저장·토큰 갱신 끔, DB 요청 타임아웃 10초
        options=ClientOptions(
            persist_session=False, auto_refresh_token=False, postgrest_client_timeout=10
        ),
    )
