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

    # AI 에이전트 (app/agent). LLM_PROVIDER: anthropic | gemini | openai | mock
    # (비우면 키로 자동 선택). LLM_MODEL 비우면 공급자 기본값
    # (anthropic: claude-opus-5-5, gemini: gemini-3.8-flash)
    llm_provider: str = ""
    llm_model: str = ""
    llm_effort: str = "medium"  # low | medium | high | xhigh | max
    llm_max_tokens: int = 8000  # 한 턴 출력 상한 (공개 API라 비용 보호 위해 보수적으로)
    anthropic_api_key: str = ""  # 비밀값. Render 대시보드 / backend/.env 에만
    gemini_api_key: str = ""  # 비밀값. Google AI Studio에서 발급
    llm_base_url: str = ""  # openai 호환 API 주소 (gemini는 기본값 사용)
    llm_api_key: str = ""  # openai 호환 API 키 (LLM_PROVIDER=openai)
    agent_max_turns: int = 6  # 한 요청에서 LLM↔도구 왕복 최대 횟수
    agent_tool_timeout: float = 30.0
    # 공개 API 남용 방지 (프로세스 메모리 기준 — 서버 재시작 시 초기화)
    chat_rate_per_ip: int = 20  # IP당 10분에 보낼 수 있는 메시지 수
    chat_daily_limit: int = 500  # 서버 전체 하루 메시지 수
    chat_max_messages: int = 80  # 대화 하나의 최대 저장 메시지 수 (넘으면 새 대화)

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
