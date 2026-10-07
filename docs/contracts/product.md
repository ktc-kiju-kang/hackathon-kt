# product (Opportunity → Product Card·PoC 생성)
- 담당: @ktc-kiju-kang · 이슈: #24 · 계약: #21
- 사용처: frontend `/product` (`features/product`). 입력은 `/radar`에서 고른 `Opportunity`
- DB: 직접 쓰는 표 없음 (v1은 저장하지 않음. 결과 내보내기는 프론트에서 Markdown으로)
- 스키마: `backend/app/schemas/product.py` (#21에서 만듦). `Opportunity`는 `app.schemas.radar`에서, `Evidence`는 `app.schemas.trends`에서 import
- 의존: trends `resolve_evidence` (#22). 구현 전에는 mock을 쓴다. radar 서비스는 쓰지 않는다

## POST /api/product/generate — v1 (SSE)
Request:
```ts
{ opportunity: Opportunity,   // radar에서 받은 객체 그대로 (서버는 저장된 값을 찾지 않는다)
  notes?: string }            // (≤500자) 추가 요구사항. 예: "3주 안에 PoC 가능해야 함"
```
→ 200 `text/event-stream` · 422 (`notes` 500자 초과, `opportunity` JSON 8000자 초과 등) · **429** (chat과 같은 한도 `check_quota`)

이벤트는 [radar 스트림 형식](radar.md#스트림-형식-radarproduct-공통)과 같다. 구조화 출력은 [radar의 방법](radar.md#구조화-출력-방법-radarproduct-공통)과 같다.

순서:
```
stage(design,start) → stage(design,done) → stage(poc,start) → stage(poc,done) → product → done
```
LLM 호출은 요청당 최대 3회다 (`CallBudget(limit=3)`, 일시 오류·`bad_output` 재시도 포함). 오류가 나면 그 시점에 `error`를 보내고 끝난다.

**Evidence 재검증**: 요청의 `opportunity`는 클라이언트가 보낸 값이라 그대로 믿지 않는다.
- 서버는 `opportunity.evidence`에서 `(metric, key, country)`만 꺼낸다.
- `resolve_evidence`로 다시 채워 `ProductCard.evidence`에 넣는다. 허용 국가는 `opportunity.country`와 `null`이다.
- 입력의 숫자와 label은 쓰지 않는다. LLM 프롬프트에도 다시 채운 값만 넣는다.

## GET /api/product/snapshot/{opportunity_id} — v1 (데모 예비안)
radar 스냅샷(`GET /api/radar/snapshot/{company_id}`)의 기회에 대해 미리 만들어 둔 Product Card. LLM을 부르지 않는다.
→ 200 `ProductSnapshot` · 404 (스냅샷 없음)

```ts
ProductSnapshot = { snapshot: SnapshotInfo, product: ProductCard }   // SnapshotInfo는 radar 계약
```

## 타입
```ts
ProductCard = {
  id: string,                          // 서버가 생성 ("prd_" + 랜덤)
  opportunity_id: string,
  name: string,                        // 예: "KT CloudOps Agent"
  tagline: string,                     // 한 줄 설명
  problem: string,
  target_users: { persona: string, pain: string }[],
  value_props: string[],
  features: { name: string, description: string, priority: "must" | "should" | "could" }[],
  user_flow: string[],                 // 단계 순서. 예: ["장애 알림 수신", "AI가 로그·이벤트 분석", ...]
  data_needed: { name: string, source: string, availability: "public" | "internal" | "to_collect" }[],
  apis: { method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE", path: string, description: string }[],
  architecture: {
    components: { id: string, name: string, role: string }[],
    edges: { from: string, to: string, label: string | null }[]   // components.id 참조 (없는 id를 가리키면 서버가 버림). 프론트가 간단한 다이어그램으로 그린다
  },
  mvp_scope: { in: string[], out: string[] },
  poc_plan: {
    duration_weeks: number,            // 1~12
    milestones: { week: number, goal: string }[],
    success_metrics: string[],
    risks: string[]
  },
  evidence: Evidence[]                 // 서버가 다시 채운 값
}
```

## 결과 유지 (frontend)
`/radar`에 다녀와도 마지막 Product Card가 남도록 `sessionStorage`의 `product:last-result`에 `{ product, snapshot }`을 저장한다 (`features/product/api.ts`의 `saveProductResult`·`loadProductResult`, 저장은 `@/lib/session`). 지금 고른 기회와 `opportunity_id`가 같을 때만 다시 보여 준다. 서버 API와는 무관하다.

## 변경 이력
| 날짜 | 변경 | 작성자 |
|---|---|---|
| 2026-10-01 | 추가 | ktc-kiju-kang |
| 2026-10-02 | 구현 반영: edge `label`은 null 가능, 잘못된 edge 제거, 입력 크기 상한 8000자(422) | ktc-kiju-kang |
| 2026-10-02 | `GET /api/product/snapshot/{opportunity_id}` 추가 (데모 예비안, #32) | ktc-kiju-kang |
