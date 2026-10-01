from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # 콤마 구분 허용 Origin(프로덕션·로컬) + Vercel 프리뷰 도메인 정규식(ktc-kiju-kang 스코프만)
    cors_origins: str = "https://hackathon-kt.vercel.app,http://localhost:3000"
    cors_origin_regex: str = r"https://hackathon-[a-z0-9-]+-ktc-kiju-kang\.vercel\.app"

    # 배포된 커밋 SHA. Render가 RENDER_GIT_COMMIT을 자동 주입 (배포 확인용)
    render_git_commit: str = ""

    # Supabase (백엔드 전용. service_role 키는 절대 프론트/레포에 두지 않는다)
    supabase_url: str = ""
    supabase_service_role_key: str = ""

    # AI 에이전트 (app/agent). LLM_PROVIDER 비우면 ANTHROPIC_API_KEY 있을 때 anthropic, 없으면 mock
    llm_provider: str = ""
    llm_model: str = "claude-opus-5-5"
    llm_effort: str = "medium"  # low | medium | high | xhigh | max
    llm_max_tokens: int = 64000
    anthropic_api_key: str = ""  # 비밀값. Render 대시보드 / backend/.env 에만
    agent_max_turns: int = 10  # 한 요청에서 LLM↔도구 왕복 최대 횟수
    agent_tool_timeout: float = 30.0

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
