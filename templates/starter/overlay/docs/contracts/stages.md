# stages (LLM 단계형 생성 공통 규칙)

> LLM이 대화가 아닌 **결과 객체**를 만드는 API(SSE)가 따르는 공통 형식. 구현: `backend/app/agent/stages.py`(`StageRunner`·`stream_stages`), `structured.py`(`call_structured`·`CallBudget`·`sse_stream`). 이 형식을 쓰는 기능 계약은 "스트림 형식: stages.md"라고 적고 결과 이벤트만 정의한다.

## 스트림 형식
`event: <type>\ndata: <json>\n\n`. 15초마다 `: ping` 줄이 올 수 있다 (무시). 클라이언트가 연결을 끊으면 서버도 LLM 호출을 멈춘다.

| event | data | 의미 |
|---|---|---|
| `stage` | `{ "stage": string, "status": "start" \| "done", "summary"?: string }` | 단계 진행. `summary`는 `done`에서만 오는 화면용 한 줄 |
| `<결과>` | 기능 계약이 정의 (예: `{ "item": Item }`) | 결과 1건 완성. 해당 단계의 start와 done 사이에 온다 |
| `retry` | chat과 같음 | LLM 일시 오류로 대기 후 재시도 |
| `done` | `{ "stop_reason": "end", "usage": object }` | 정상 종료 (마지막 이벤트) |
| `error` | chat과 같음 `{ "message", "code"? }` | 오류 종료 (마지막 이벤트). code: `bad_output`(출력이 스키마와 맞지 않거나 잘림), `no_result`(결과 0개), `limit`(요청당 LLM 호출 한도 초과) |

모든 단계는 `start`와 `done`을 한 번씩 보낸다. 404·422·429는 스트림을 시작하기 전에 HTTP 상태로 돌려준다.

## 구조화 출력 방법
- **결과 제출용 도구 하나**(예: `submit_result`)만 넘기고, 그 도구 입력(pydantic)을 결과로 쓴다.
- 도구를 호출하지 않았거나 입력이 검증에 실패하면 이유를 덧붙여 1회 다시 요청한다. 그래도 실패하면 `error`(`bad_output`).
- 출력이 `max_tokens`에 걸리면 다시 요청하지 않고 바로 `bad_output`.
- 요청당 LLM 호출 수는 `CallBudget`으로 제한한다 (재시도 포함). 기능 계약에 상한을 적는다.
- provider가 mock이면 LLM을 부르지 않고 **고정 샘플 결과**(`mock=`)를 같은 이벤트 순서로 보낸다 (키 없이 UI 개발·시험).
