# dashboard
- 담당: @ktc-kiju-kang · 이슈: #99
- 사용처: 사이드 메뉴 "현황판" `/dashboard` (`frontend/src/features/dashboard/`)
- DB: 읽기만 — `schema_migrations` (기능 테이블 없음)
- 이 PC에서만 열리는 로컬 도구다 (서버는 127.0.0.1). 응답에 비밀값(토큰)을 넣지 않는다.

## GET /api/dashboard — v1
로컬 정보. 외부 호출 없음 (빠름). 칸마다 따로 실패할 수 있고, 한 칸이 실패해도 200.

Response 200:
```
{
  "generated_at": string,                         // ISO 8601
  "server": Health,                               // GET /api/health 와 같은 모양 (client_ip 제외 → null)
  "migrations": [{ "version": string, "applied_at": string }],   // DB 오류면 []
  "tests": {
    "status": "ok" | "none",                      // none = 시험 기록 없음
    "run_id": string | null,                      // 예: 20261008-173723-b54b3d8
    "sha": string | null, "overall": "PASS" | "FAIL" | null, "ran_at": string | null,  // ran_at: "2026-10-08 17:37 KST"
    "dirty": boolean,                             // 커밋 안 된 코드로 실행 → 제출 근거 아님
    "suites": [{ "name": string, "result": string }],             // 예: backend pytest / "61개 중 실패 0"
    "tcs": [{ "tc": string, "result": string, "test": string }]
  },
  "reqs": {
    "status": "ok" | "none",                      // none = docs/prd.md 없음 (키트 원본 레포)
    "items": [{ "id": "REQ-01", "title": string, "priority": string, "issue": string, "state": string }]
  },
  "test_history": [{ "run_id": string, "sha": string | null, "ran_at": string, "overall": "PASS" | "FAIL" | null,
                     "total": int, "failed": int, "dirty": boolean }],   // 최근 20개, 오래된 것부터 (#101)
  "readiness": {                                  // 제출 준비도 — make submit-check와 같은 기준 (#101)
    "deadline": string,                           // ISO 8601, SUBMIT_DEADLINE (기본 2026-10-15T00:00:00+09:00)
    "checks": [{ "key": string, "label": string, "status": "ok" | "fail" | "na", "detail": string }]
  }
}
```
- `tests`: `make e2e` 근거 `docs/evidence/<실행>/summary.md`·`.run/evidence/<실행>/summary.md` 두 곳 중 가장 최근 실행 (폴더 이름이 시각으로 시작)
- `test_history`: 같은 두 폴더의 실행 전부 중 최근 20개. `total`·`failed` = 묶음 합계, `ran_at` = 폴더 이름의 KST 시각
- `readiness.checks` (`key`): `committed`(실행 버전에 커밋 안 된 변경 없음) · `evidence`(이 커밋으로 돌린 근거가 `docs/evidence/`에 있고 전체 PASS) · `placeholders`(README·docs/ 제출 문서 7개의 `{{…}}` 남은 수) · `reqs`(제외 빼고 REQ 전부 검증됨). 제출 문서가 없는 레포(키트 원본)는 `na`. "origin/main과 같음"은 GitHub 칸의 `main_sha`로 화면에서 비교한다 (docker 안엔 git이 없음)
- `reqs`: `docs/prd.md` 요구사항 표 (ID·요구사항·우선순위·Issue·상태). `{{자리표시}}`는 그대로 보인다

## GET /api/dashboard/github — v1
GitHub(또는 사내 GHE) 현황. 60초 캐시 (토큰이 없으면 5분 — API 한도 보호), 한 번 갱신은 15초 상한.

Response 200:
```
{
  "status": "ok" | "unconfigured" | "error",
  "message": string | null,                       // unconfigured·error 이유 (토큰 값은 절대 넣지 않는다)
  "repo": string | null,                          // owner/name
  "fetched_at": string | null,
  "issues": [{ "number": int, "title": string, "assignees": [string], "labels": [string], "url": string }],
  "pulls": [{ "number": int, "title": string, "author": string, "branch": string, "draft": bool,
              "checks": "pass" | "fail" | "pending" | "none", "url": string }],
  "main_runs": [{ "name": string, "status": string, "conclusion": string | null, "sha": string, "url": string, "created_at": string }],
  "claims": [{ "issue": int, "owner": string | null, "claimed_at": string | null }],  // scripts/claim.sh의 claim/<번호> 브랜치
  "main_sha": string | null,                      // main 최신 커밋 (#101)
  "recent_merges": [{ "number": int, "title": string, "author": string, "merged_at": string }]  // 최근 닫힌 PR 중 머지된 것 (#101)
}
```
- 설정 (`backend/.env`): `GITHUB_REPO=owner/name`(비우면 git origin 주소에서), `GITHUB_TOKEN`(읽기 전용 토큰 — 공개 github.com 레포는 없어도 됨, 시간당 60회), `GITHUB_API_URL`(비우면 github.com, origin이 다른 호스트면 그 호스트의 `/api/v3` — 이때 토큰은 보내지 않으므로 사내 GHE에 토큰을 쓰려면 직접 적는다)
- `unconfigured` = 레포를 알 수 없음, `error` = 인증 실패·한도 초과·네트워크 (그 칸만 표시, 나머지 화면은 정상)
- 개수 상한: Issue 50 · PR 10(PR마다 check-run 조회) · main 실행 20 · claim 10 · 최근 닫힌 PR 30
- 팀원별 보기(담당·선점·열린 PR·CI 실패·24시간 머지, 24시간 넘은 선점 경고)는 이 응답으로 화면에서 집계한다

## 변경 이력
| 날짜 | 변경 | 작성자 |
|---|---|---|
| 2026-10-08 | 추가 (#99) | ktc-kiju-kang |
| 2026-10-08 | `test_history`·`readiness`, GitHub `main_sha`·`recent_merges`·`claims[].claimed_at`, main 실행 20개 (v1 호환, #101) | ktc-kiju-kang |
