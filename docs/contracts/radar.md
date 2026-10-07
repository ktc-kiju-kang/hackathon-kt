# radar (그룹사 선택 + AI Opportunity Radar)
- 담당: @ktc-kiju-kang · 이슈: #23 · 계약: #21
- 사용처: frontend `/radar` (`features/radar`). `Opportunity` 타입은 product (#24)가 입력으로 쓴다
- 데이터: `backend/data/companies.json` (DB 없음, 아래 "그룹사 데이터"). Opportunity는 DB에 저장하지 않는다 (요청마다 생성해 스트리밍, 같은 요청은 메모리에서 재사용 — 아래)
- 스키마: `backend/app/schemas/radar.py` (#21에서 만듦)
- 의존: trends `summary`·`resolve_evidence` (#22). 구현 전에는 같은 형태의 mock을 쓴다

## GET /api/radar/companies — v1
→ 200 `Company[]` (고정 5개: `kt`, `kt-cloud`, `kt-ds`, `bccard`, `kt-skylife`)

## POST /api/radar/opportunities — v1 (SSE)
Request:
```ts
{ company_id: string,
  country?: string,        // 근거로 쓸 Signals 국가 (trends 지원 국가). 기본 "KR"
  focus?: string,          // (≤200자) 사용자가 관심 있는 방향. 예: "B2B 운영 자동화"
  count?: number }         // 3~5, 기본 4
```
→ 200 `text/event-stream`
· 404: company_id나 country가 없음
· 422
· **429**: chat과 같은 한도(`check_quota`). 요청 1번이 1회로 집계된다

권한·한도 확인은 스트림 시작 전에 한다.

**같은 요청 재사용** (#66, LLM 비용 절약): `company_id`·`country`·`focus`(앞뒤 공백 무시)·`count`·LLM 공급자가 같은 요청은 **6시간 동안** 이전 결과를 다시 보낸다.
- 이벤트 순서·내용(기회 `id` 포함)은 처음과 같고, 마지막 `done`의 data에 `"cached": true`가 붙는다. LLM을 부르지 않고 한도도 쓰지 않는다.
- `done`으로 끝난 결과만 저장한다. `error`로 끝났거나 중간에 연결이 끊긴 결과는 저장하지 않는다.
- 서버 메모리에 최대 100개까지 두며 재시작·재배포하면 비워진다.

단계:
1. `trend`: 요청 국가와 전 세계의 `TrendSummary(months=23)`를 읽고 LLM이 회사와 관련된 트렌드를 고른다.
2. `match`: 회사의 사업·자산과 연결한다.
3. `opportunity`: 기회를 만든다.

LLM 호출은 요청당 최대 `AGENT_MAX_TURNS`(6)회다. 일시 오류 재시도와 형식 오류 재시도를 모두 세고, 세 단계가 이 예산을 함께 쓴다. 넘으면 `error`(`limit`)를 보낸다.

**Evidence 규칙**: LLM은 `evidence_refs`(EvidenceRef)만 낸다. 서버가 `resolve_evidence`로 숫자와 label을 채운다. 허용 국가는 요청 국가와 `null`이다. 해석된 근거가 0개인 Opportunity는 보내지 않는다. 그래서 실제로 오는 개수 N은 `count` 이하이다.

## 스트림 형식 (radar·product 공통)
`event: <type>\ndata: <json>\n\n`. 15초마다 `: ping` 줄이 올 수 있다 (무시). 클라이언트가 연결을 끊으면 서버도 LLM 호출을 멈춘다.

| event | data | 의미 |
|---|---|---|
| `stage` | `{ "stage": string, "status": "start" \| "done", "summary"?: string }` | 단계 진행. `summary`는 `done`에서만 오는 화면용 한 줄 (예: "KR Technical help 비중 17.4% → 4.1%") |
| `opportunity` | `{ "opportunity": Opportunity }` | (radar) 기회 1건 완성 |
| `product` | `{ "product": ProductCard }` | (product) 설계 완성 |
| `retry` | chat과 같음 | LLM 일시 오류로 대기 후 재시도 |
| `done` | `{ "stop_reason": "end", "usage": object, "cached"?: true }` | 정상 종료 (마지막 이벤트). chat 파서와 호환되게 `stop_reason`을 넣는다. `cached`는 radar가 이전 결과를 재사용했을 때만 온다 |
| `error` | chat과 같음 `{ "message", "code"? }` | 오류 종료 (마지막 이벤트). 이 기능에서 추가된 code: `bad_output`(LLM 출력이 스키마와 맞지 않거나 길이 제한에 걸려 잘림), `no_result`(근거 있는 기회가 0개), `limit`(요청당 LLM 호출 한도 초과) |

**radar 순서**: 모든 단계는 `start`와 `done`을 한 번씩 보낸다. `opportunity` 이벤트는 해당 단계의 start와 done 사이에 온다.
```
stage(trend,start) → stage(trend,done) → stage(match,start) → stage(match,done)
→ stage(opportunity,start) → opportunity × N (1 ≤ N ≤ count) → stage(opportunity,done) → done
```
N이 0이면 `stage(opportunity,done)` 대신 `error`(`no_result`)를 보낸다. 오류가 나면 그 시점에 `error`를 보내고 끝난다.

## 구조화 출력 방법 (radar·product 공통)
`LLMProvider`에는 structured output API가 없다. 그래서 다음 방법으로 통일한다.
- **결과 제출용 도구 하나**(예: `submit_opportunities`)만 넘긴다. 시스템 프롬프트로 그 도구를 호출하게 한다.
- 도구 입력(pydantic)을 결과로 쓴다.
- 도구를 호출하지 않았거나 입력이 검증에 실패하면, 실패 이유를 덧붙여 1회 다시 요청한다. 그래도 실패하면 `error`(`bad_output`)를 보낸다.
- 출력이 길이 제한(`max_tokens`)에 걸리면 같은 요청을 반복해도 잘리므로 다시 요청하지 않고 바로 `bad_output`을 보낸다.
- 구현: `app/agent/stages.py`의 `StageRunner`(단계 start/done·mock 폴백·예산)와 `stream_stages`. 내부는 `app/agent/structured.py`의 `call_structured`(제출 도구 스키마의 `$ref`를 펼쳐 보낸다), `CallBudget`, `sse_stream`.
- provider가 mock이면 LLM을 부르지 않고 **고정 샘플 결과**를 같은 이벤트 순서로 보낸다. 키 없이 UI를 개발하기 위해서다.

## GET /api/radar/snapshot/{company_id} — v1 (데모 예비안)
미리 실제 LLM으로 만들어 둔 결과. LLM을 부르지 않고 한도도 쓰지 않는다. 실시간 생성이 실패했을 때(한도·장애) 화면이 "저장된 결과"로 보여준다.
→ 200 `RadarSnapshot` · 404 (그 그룹사의 스냅샷 없음)

```ts
SnapshotInfo  = { created_at: string, model: string }      // 언제·어떤 모델로 만들었는지 (화면에 표시)
RadarSnapshot = { company_id: string, country: string, snapshot: SnapshotInfo, opportunities: Opportunity[] }
```
- 저장 위치: `backend/data/demo/<company_id>.json` (`python -m evals.make_demo_snapshot --company <id>`로 생성, 실제 LLM 호출)
- 화면은 실시간 결과로 오해하지 않게 "{날짜}에 {모델}로 미리 만든 결과"라고 표시한다.
- `/radar`는 그룹사를 고를 때 이 API로 스냅샷이 있는지 미리 확인한다. 있으면 "기회 찾기" 옆과 오류 카드에 "저장된 결과" 버튼을 보인다. product 단계에서 막혔을 때도 radar로 돌아와 저장된 기회부터 다시 갈 수 있다.

## 화면 간 전달 (frontend)
`/radar`에서 "프로덕트 설계"를 누르면 고른 `Opportunity`를 `sessionStorage`의 `radar:selected-opportunity` 키(JSON)에 저장하고 `/product`로 이동한다.
`features/radar/api.ts`의 `saveSelectedOpportunity` · `loadSelectedOpportunity`를 쓴다. 저장소를 못 쓰면 탭 메모리 값을 쓴다.
화면을 오가도 결과가 남게, 마지막 결과도 같은 방식으로 저장한다: radar는 `radar:last-result`(`saveRadarResult`), product는 `product:last-result`(같은 기회일 때만 다시 보여 준다, [product](product.md)). 저장은 `@/lib/session`. 서버 API와는 무관하다.

## 그룹사 데이터
v1은 DB 대신 `backend/data/companies.json`(공개 자료 요약)을 읽는다. 공개 읽기 전용이고 5개뿐이라서다.

## 타입
```ts
Company = {
  id: string, name: string, name_en: string,
  summary: string,                     // 한두 문장
  business_areas: string[],            // 예: ["퍼블릭 클라우드", "IDC", "AI 인프라(GPU)"]
  customers: string[],                 // 예: ["공공기관", "엔터프라이즈", "스타트업"]
  assets: string[],                    // 활용 가능한 자산·역량. 예: ["전국 IDC", "GPU 팜", "MSP 운영 조직"]
  sources: string[]                    // 공개 자료 URL (내부 자료 금지)
}

Opportunity = {
  id: string,                          // 서버가 생성 ("opp_" + 랜덤)
  company_id: string,
  country: string,                     // 근거로 쓴 Signals 국가 (요청 country)
  title: string,                       // 예: "Cloud 장애 대응 자동화"
  trend: string,                       // 근거가 된 트렌드 한 줄
  target: string[],                    // 예: ["KT Cloud 운영 조직", "기업 Cloud 고객"]
  problem: string,
  solution: string,
  kt_assets: string[],                 // 활용할 Company.assets 항목
  evidence: Evidence[],                // 1개 이상, 서버가 채운 값 (trends 계약)
  rationale: string,                   // LLM 추론: 근거에서 이 기회로 이어지는 이유. 화면에서 근거와 구분해 표시
  score: { impact: 1|2|3|4|5, feasibility: 1|2|3|4|5 }
}
```
`Evidence`, `EvidenceRef`, `Month`는 [trends](trends.md)를 따른다.

## 변경 이력
| 날짜 | 변경 | 작성자 |
|---|---|---|
| 2026-10-01 | 추가 | ktc-kiju-kang |
| 2026-10-02 | 그룹사 데이터를 DB에서 JSON 파일로 변경, 화면 간 전달 방식 추가 (API 형태는 그대로) | ktc-kiju-kang |
| 2026-10-02 | `GET /api/radar/snapshot/{company_id}` 추가 (데모 예비안, #32) | ktc-kiju-kang |
