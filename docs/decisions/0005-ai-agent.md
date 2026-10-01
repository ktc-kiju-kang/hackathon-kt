# 0005. AI 에이전트 기본 구조

- 상태: 채택
- 날짜: 2026-10-01

## 결정
- **직접 만든 도구 호출 루프** (`backend/app/agent/loop.py`) + **LLM 어댑터** (`providers/`). 기본은 Claude(`claude-opus-5-5`, Anthropic Python SDK), 키가 없으면 `mock`.
- 대화 기록은 **공급자 중립 형식**(`agent/types.py` Message)으로 저장. Claude 응답 원본(`raw`, thinking 블록 포함)은 같은 공급자로 이어갈 때 그대로 재전송.
- 도구 = `agent/tools/<name>.py` 파일 하나, 자동 등록, 입력은 pydantic으로 스키마 생성 + 실행 전 검증.
- 프론트는 SSE로 텍스트·도구 실행을 실시간 표시. 대화는 Supabase(`conversations`, `messages`).
- 품질은 `backend/evals/` 규칙 기반 평가로 확인.

## 이유
- 해커톤에서 특정 LLM(사내 모델 등)을 요구할 수 있음 → 어댑터만 추가하면 루프·도구·저장·UI는 그대로.
- SDK의 Tool Runner 대신 직접 루프: 공급자 교체, SSE 이벤트 설계, 도구 실행 제어(병렬·타임아웃·검증)를 한 곳에서.
- 도구가 파일 단위라 3명이 동시에 도구를 추가해도 충돌이 없다.

## 트레이드오프
- 루프 유지보수는 우리 몫 (Claude 쪽: `max_tokens`·`refusal` 처리, 거절 시 `fallbacks: "default"` 자동 재시도, thinking 원본 보존).
- 로그인 없는 `X-Client-Id` 소유권은 데모용. 실제 사용자 인증이 필요하면 별도 ADR.
- 대화가 매우 길어지면(수십만 토큰) 컨텍스트 관리(compaction 등)가 필요 — 미구현.
