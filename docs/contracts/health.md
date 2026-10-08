# health
- 담당: @ktc-kiju-kang
- 사용처: 로컬 배포 스모크(`scripts/smoke.sh`), 시험 근거의 실행 버전 확인(`make e2e`), 홈 화면 `features/health/HealthCard`

## GET /api/health — v1
Response 200: `{ "status": "ok", "time": string(ISO 8601), "version": string | null, "db": "ok" | "error" | "unconfigured", "llm": string | null, "client_ip": string | null, "uptime_seconds": integer }`
(`version` = 배포된 git 커밋 SHA, 로컬은 null. 배포 파이프라인이 새 버전 확인에 사용)
(`llm` = 에이전트 LLM 공급자 `anthropic` | `gemini` | `openai` | `mock` — 운영이 mock이면 LLM 키 누락)
(`client_ip` = 서버가 사용량 한도에 쓰는 요청자 IP. 요청한 사람 본인의 IP만 보인다. `X-Forwarded-For`를 조작해도 바뀌지 않아야 정상 (`app.core.quota.client_ip`))
(`uptime_seconds` = 서버 프로세스가 시작된 뒤 지난 시간(초, 정수, 0 이상). 재시작·콜드 스타트 확인용 — 값이 작으면 방금 켜진 것)
(`db` = SQLite 연결·마이그레이션 확인 결과, `version` = 실행 중인 git 커밋. DB 장애여도 health는 200)
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
