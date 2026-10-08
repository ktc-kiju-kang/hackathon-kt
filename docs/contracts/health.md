# health
- 담당: @ktc-kiju-kang
- 사용처: 로컬 배포 스모크(`scripts/smoke.sh`), 시험 근거의 실행 버전 확인(`make e2e`), 홈 화면 `features/health/HealthCard`

## GET /api/health — v1
Response 200: `{ "status": "ok", "time": string(ISO 8601), "version": string | null, "db": "ok" | "error" | "unconfigured", "llm": string | null, "client_ip": string | null, "uptime_seconds": integer }`
(`version` = 실행 중인 소스의 git 커밋 SHA (`APP_VERSION`이 있으면 그 값, `make serve`는 커밋 안 된 변경이 있으면 `-dirty`). 스모크·`make e2e`가 "시험한 코드 = HEAD" 확인에 쓴다)
(`llm` = 에이전트 LLM 공급자 `anthropic` | `gemini` | `openai` | `mock` — 키가 없으면 mock)
(`client_ip` = 서버가 사용량 한도에 쓰는 요청자 IP. 요청한 사람 본인의 IP만 보인다. `X-Forwarded-For`를 조작해도 바뀌지 않아야 정상 (`app.core.quota.client_ip`))
(`uptime_seconds` = 서버 프로세스가 시작된 뒤 지난 시간(초, 정수, 0 이상). 재시작 확인용 — 값이 작으면 방금 켜진 것)
(`db` = PostgreSQL 연결·마이그레이션 확인 결과. DB 장애여도 health는 200)
(프론트 mock 응답은 `status: "mock"`)

## 변경 이력
| 날짜 | 변경 | 작성자 |
|---|---|---|
| 2026-10-01 | 추가 | ktc-kiju-kang |
| 2026-10-01 | `version` 필드 추가 (v1 호환) | ktc-kiju-kang |
| 2026-10-01 | `db` 필드 추가 (v1 호환) | ktc-kiju-kang |
| 2026-10-01 | `llm` 필드 추가 (v1 호환) | ktc-kiju-kang |
| 2026-10-02 | `client_ip` 필드 추가 (v1 호환) | ktc-kiju-kang |
| 2026-10-08 | `uptime_seconds` 필드 추가 (v1 호환) | ktc-jehyuk-kim |
