# chat (AI 에이전트 대화)
- 담당: @ktc-kiju-kang
- 사용처: frontend `/agent` (`features/agent`). `/chat`의 `features/chat/ChatPanel`은 별도 임시 화면
- DB: `conversations`, `messages` — `database/migrations/0002_chat.sql`

## 인증 (해커톤용)
로그인 없음. 브라우저가 만든 임의 UUID를 **모든 요청 헤더 `X-Client-Id`**로 보낸다 (8~64자, 없으면 422).
대화는 만든 client_id만 조회·전송 가능 — 다르면 404 (존재 여부도 숨김).

## POST /api/chat/conversations — v1
Request: `{ "title"?: string(≤100) }` → 201 `Conversation`

## GET /api/chat/conversations — v1
→ 200 `Conversation[]` (내 것만, 최신순, 최대 50)

## GET /api/chat/conversations/{id}/messages — v1
→ 200 `ChatMessage[]` (오래된 순) · 404

## POST /api/chat/conversations/{id}/messages — v1 (SSE)
Request: `{ "content": string(1~8000) }` → 200 `text/event-stream` · 404 · 422
· **429** 사용량 한도 (IP당 10분 `CHAT_RATE_PER_IP`, 서버 전체 하루 `CHAT_DAILY_LIMIT`)
· **409** 대화 메시지 수 `CHAT_MAX_MESSAGES` 초과 → 새 대화를 만든다
(오류 본문 `{ "detail": string }` — 사용자에게 그대로 보여줘도 되는 한국어 메시지)

권한·한도 확인은 스트림 시작 전. 이벤트 형식: `event: <type>\ndata: <json>\n\n`. 15초마다 `: ping` 주석 줄이 올 수 있다 (무시).
클라이언트가 연결을 끊으면 서버도 LLM 호출을 멈춘다.

| event | data | 의미 |
|---|---|---|
| `text` | `{ "text": string }` | 답변 조각 (이어 붙인다) |
| `message` | `{ "message": ChatMessage }` | assistant 한 턴 완료 (도구 호출이 있으면 이어서 tool_call) |
| `tool_call` | `{ "id", "name", "input": object }` | 도구 실행 시작 |
| `tool_result` | `{ "tool_call_id", "content": string, "is_error": bool }` | 도구 결과 |
| `done` | `{ "stop_reason": string, "usage": object }` | 정상 종료 (마지막 이벤트) |
| `error` | `{ "message": string }` | 오류 종료 (마지막 이벤트) |

한 요청에서 `text → message → tool_call* → tool_result* → text → message → ... → done` 순으로 반복된다 (최대 `AGENT_MAX_TURNS`).

## 타입
```ts
Conversation = { id: string(uuid), title: string | null, created_at: string }
ChatMessage  = { role: "user" | "assistant" | "tool", content: string,
                 tool_calls: { id, name, input }[], tool_call_id: string | null, is_error: boolean,
                 created_at?: string }
```

## 변경 이력
| 날짜 | 변경 | 작성자 |
|---|---|---|
| 2026-10-01 | 추가 | ktc-kiju-kang |
