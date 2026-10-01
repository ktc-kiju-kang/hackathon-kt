from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # 콤마 구분 허용 Origin(프로덕션·로컬) + Vercel 프리뷰 도메인 정규식(ktc-kiju-kang 스코프만)
    cors_origins: str = "https://hackathon-kt.vercel.app,http://localhost:3000"
    cors_origin_regex: str = r"https://hackathon-[a-z0-9-]+-ktc-kiju-kang\.vercel\.app"

    # Supabase (백엔드 전용. service_role 키는 절대 프론트/레포에 두지 않는다)
    supabase_url: str = ""
    supabase_service_role_key: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
