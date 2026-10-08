import re
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # 콤마 구분 허용 Origin. 로컬 Next.js 기본. 배포하면 그 주소를 더한다.
    cors_origins: str = "http://localhost:3000"
    cors_origin_regex: str = ""

    # PostgreSQL (각자 PC의 docker compose `db`). 마이그레이션: database/migrations/*.sql
    # DATABASE_SCHEMA: 테이블을 둘 schema — 테스트(테스트마다 새 schema)·make e2e(e2e) 격리용
    database_url: str = "postgresql://app:app@localhost:55432/app"  # 로컬 전용 계정 (비밀값 아님)
    database_schema: str = "public"

    # 현황판 GitHub 칸 (/api/dashboard/github, docs/contracts/dashboard.md)
    github_repo: str = ""  # owner/name. 비우면 git origin 주소에서 찾는다
    github_token: str = ""  # 비밀값. 읽기 전용 토큰, backend/.env 에만 (공개 레포는 없어도 됨)
    github_api_url: str = ""  # 비우면 github.com, 사내 GHE는 origin 호스트의 /api/v3
    git_remote_url: str = ""  # docker 실행 때 docker.sh가 넘기는 origin 주소 (컨테이너엔 git 없음)
    submit_deadline: str = "2026-10-15T00:00:00+09:00"  # 현황판 마감 카운트다운 (본선 개발 마감)

    # /api/health의 version. 비우면 실행 중인 git 커밋 SHA (e2e-test.md 근거용)
    app_version: str = ""

    # AI 에이전트 (app/agent). LLM_PROVIDER: anthropic | gemini | openai | mock
    # (비우면 키로 자동 선택). LLM_MODEL 비우면 공급자 기본값
    # (anthropic: claude-opus-5-5, gemini: gemini-3.8-flash)
    llm_provider: str = ""
    llm_model: str = ""
    llm_effort: str = "medium"  # low | medium | high | xhigh | max
    llm_max_tokens: int = 8000  # 한 턴 출력 상한 (비용 보호)
    anthropic_api_key: str = ""  # 비밀값. backend/.env 에만
    gemini_api_key: str = ""  # 비밀값. Google AI Studio에서 발급
    llm_base_url: str = ""  # openai 호환 API 주소 (gemini는 기본값 사용)
    llm_api_key: str = ""  # openai 호환 API 키 (LLM_PROVIDER=openai)
    agent_max_turns: int = 6  # 한 요청에서 LLM↔도구 왕복 최대 횟수
    agent_tool_timeout: float = 30.0
    # LLM 일시 오류(한도 초과·5xx) 재시도: 글자를 내보내기 전에만,
    # 대기는 retry-after 또는 지수 증가
    agent_llm_retries: int = 2
    agent_retry_delay: float = 4.0
    agent_retry_max_delay: float = 20.0
    # LLM 비용 보호 (프로세스 메모리 기준 — 서버 재시작 시 초기화)
    chat_rate_per_ip: int = 20  # IP당 10분에 보낼 수 있는 메시지 수
    chat_daily_limit: int = 150  # 서버 전체 하루 LLM 요청 수
    chat_max_messages: int = 80  # 대화 하나의 최대 저장 메시지 수 (넘으면 새 대화)

    @field_validator("database_url")
    @classmethod
    def _default_db_url(cls, v: str) -> str:
        return v or "postgresql://app:app@localhost:55432/app"  # .env의 빈 DATABASE_URL= 도 기본값

    @field_validator("database_schema")
    @classmethod
    def _check_schema(cls, v: str) -> str:
        v = v or "public"
        # 연결 옵션 search_path에 들어가므로 이름 형식만 허용한다
        if not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", v):
            raise ValueError(f"DATABASE_SCHEMA는 소문자·숫자·_ 만: {v!r}")
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
