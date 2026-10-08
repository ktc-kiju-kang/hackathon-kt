---
name: add-agent-tool
description: AI 에이전트에 새 도구 추가 — backend/app/agent/tools/<name>.py (pydantic 입력, 자동 등록), 테스트. 에이전트가 외부 API·DB 조회·계산 등 새 행동을 할 수 있게 할 때 사용.
argument-hint: <도구 이름> <설명>
---
에이전트 도구를 추가한다: $ARGUMENTS

0. **구현 원칙** — `/ponytail`(기본 full)을 적용한다: 기존 도구·헬퍼 재사용 → 표준 라이브러리 → 최소 구현. 입력 제한·외부 실패 처리·테스트는 줄이지 않는다.

1. **설계** — 사용자에게 확인받는다:
   - 이름: `snake_case` 동사형 (예: `search_products`). 기존 도구와 겹치지 않게 (`app/agent/tools/`).
   - 설명(description): LLM이 **언제 쓰고 언제 쓰지 말지** 판단하는 유일한 근거. 용도·입력 의미·결과 형태를 구체적으로.
   - 입력 필드와 결과(JSON 문자열 권장, 필요한 필드만 — 결과가 길면 토큰 비용·혼란 증가).
2. **구현** — `backend/app/agent/tools/<name>.py` (`calculator.py`, `current_time.py` 패턴):
   ```python
   class Input(BaseModel):
       query: str = Field(max_length=200, description="...")
   async def run(args: Input) -> str: ...
   tool = Tool(name="...", description="...", input_model=Input, run=run)
   ```
   - 입력은 LLM이 만든 **신뢰할 수 없는 값**: 길이 제한, 허용값(`Literal`), 경로·URL·SQL 직접 실행 금지. `eval()` 금지.
   - 실패는 예외로 던진다 → 루프가 `is_error` 결과로 LLM에 돌려준다 (LLM이 고쳐서 재시도).
   - 외부 API는 `httpx2`/SDK로 타임아웃 지정, 키는 `app/core/config.py` Settings → `backend/.env.example`에 이름 추가.
   - DB는 service처럼 `get_db()`. 사용자별 데이터면 대화 소유자 확인이 필요 — 도구에 client_id를 넘기는 구조는 아직 없으니 먼저 상의.
   - 등록은 자동 (파일만 추가). `loop.py`·`main.py`는 고치지 않는다. **모든 에이전트 대화(`/agent`)에 바로 보이게 된다**는 점을 PR에 적는다.
   - 입력 모델 필드 이름은 자유지만, 어댑터가 스키마를 바꿔 보내므로(`openai_compat._strip_titles`) 새 형태의 스키마면 실제 API로 한 번 확인한다.
   - 첫 호출에 파일 읽기 등 느린 동기 작업이 있으면 `asyncio.to_thread`로 감싼다 (이벤트 루프를 막지 않게).
3. **테스트** — `backend/tests/test_tool_<name>.py`: `run()` 직접 호출로 정상·잘못된 입력·외부 실패(monkeypatch) 케이스. 실제 외부 API·DB에 붙지 않게.
4. **검증** — `ruff` + `pytest` 통과. mock LLM은 정해진 규칙으로만 도구를 고르므로 새 도구는 실제 LLM으로 한 번 확인한다 (`backend/.env`에 키 → 로컬 `/agent`에서 질문). 비용이 들면 실행 전 사용자 확인. 결과는 `docs/e2e-test.md`에 남긴다.
