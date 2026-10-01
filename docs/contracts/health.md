# health
- 담당: @ktc-kiju-kang
- 사용처: frontend 홈 `features/health/HealthCard`

## GET /api/health — v1
Response 200: `{ "status": "ok", "time": string(ISO 8601), "version": string | null, "db": "ok" | "error" | "unconfigured" }`
(`version` = 배포된 git 커밋 SHA, 로컬은 null. 배포 파이프라인이 새 버전 확인에 사용)
(`db` = Supabase 연결·키 확인 결과. DB 장애여도 health는 200 — Render 헬스체크가 서비스를 내리지 않도록)
(프론트 mock 응답은 `status: "mock"`)

## 변경 이력
| 날짜 | 변경 | 작성자 |
|---|---|---|
| 2026-10-01 | 추가 | ktc-kiju-kang |
| 2026-10-01 | `version` 필드 추가 (v1 호환) | ktc-kiju-kang |
| 2026-10-01 | `db` 필드 추가 (v1 호환) | ktc-kiju-kang |
