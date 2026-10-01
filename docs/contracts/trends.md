# trends (OpenAI Signals 트렌드)
- 담당: (#22 담당자) · 이슈: #22 · 계약: #21
- 사용처: frontend `/trends` (`features/trends`), radar·product의 근거(Evidence) 채우기 (`app.services.trends.resolve_evidence`), 에이전트 도구 `tools/get_ai_usage_trends.py`
- 데이터: DB를 쓰지 않는다. 공개된 읽기 전용 데이터라 `backend/data/signals/`의 원본 CSV 9개를 서버 메모리에 읽는다 (약 2MB). 원본 `https://cdn.openai.com/signals/data-download-csv.zip`, 설명은 `docs/PROJECT.md`
- 스키마: `backend/app/schemas/trends.py` (#21에서 만듦)

인증 없음 (공개 집계 데이터). 응답은 원본 CSV 값만 쓴다. LLM은 호출하지 않는다.

**읽을 때 주의**: 나미비아 국가 코드가 문자열 `NA`다. pandas는 기본 설정에서 이 값을 NaN으로 읽는다. 현재 구현은 `csv` 모듈로 문자열 그대로 읽는다.

## 지원 국가
`meta.countries`는 아래 4개 파일 모두에 24개월 데이터가 빠짐없이 있는 국가만 담는다. 업무 메시지(`work_related=1`) 행도 매월 있어야 한다. 작은 나라는 업무 데이터가 아예 없는 경우가 많아서, 현재 67개국이다. `KR`, `US`는 포함된다.
- topic×country
- work_related×country
- topic×work_related×country
- ask_do_express×work_related×country

목록에 없는 국가를 요청하면 404다. 이 규칙 덕분에 `series`와 `summary`에는 빠진 월이 없다.
"최신 월"은 데이터 전체의 마지막 월(현재 `2026-06`)이다.

## GET /api/trends/meta — v1
→ 200 `TrendsMeta`

## GET /api/trends/series — v1
월별 시계열. 차트용.

| query | 값 | 기본 |
|---|---|---|
| `dimension` | `topic` \| `work_related` \| `ask_do_express` (필수) | |
| `country` | 대문자 2자리 국가 코드. 생략하면 전 세계 | 전 세계 |
| `work_related` | `0` \| `1`. `topic`에는 선택, **`ask_do_express`에는 필수** | |
| `from`, `to` | `YYYY-MM`, 데이터 기간 안 | 데이터 전체 기간 |

→ 200 `TrendSeries` · 404 `{ "detail": "해당 국가 데이터가 없습니다" }` · 422

422가 되는 경우:
- `dimension=ask_do_express`인데 `work_related`가 없음. 원본에 전체 메시지 기준 데이터가 없기 때문이다.
- `dimension=work_related`인데 `work_related`를 넘김
- `from > to`이거나, 월이 데이터 기간 밖임
- 국가 코드 형식이 틀림 (소문자 포함)

값의 의미:
- `topic` + `work_related=1`: 업무 메시지 중 각 topic의 비중. `share_of_messages_by_topic_work_related_*` 파일에서 읽는다. 이름이 비슷한 `share_of_messages_by_work_related_topic_month.csv`는 다른 지표이므로 쓰지 않는다.
- `topic`에 `work_related`가 없으면 전체 메시지 중 비중이다.
- `work_related`: key가 `"0"`, `"1"`인 비중이다.

## GET /api/trends/summary — v1
기간 비교 요약. 대시보드 상단 카드와 **Evidence의 원천**으로 쓴다.

| query | 값 | 기본 |
|---|---|---|
| `country` | 국가 코드. 생략하면 전 세계 | 전 세계 |
| `months` | 비교 간격 1~23. 최신 월과 그보다 N개월 전 월을 비교한다 (23 = 전체 기간) | 12 |

→ 200 `TrendSummary` · 404 · 422

## Evidence (radar·product 공통)
LLM은 **어떤 지표인지(`EvidenceRef`)만** 고른다. 숫자와 문구(`Evidence`)는 서버가 `resolve_evidence`로 채운다.
- 기준 기간은 항상 `months=23`(2024-07 → 2026-06, 순위는 2025-01 → 2026-04 분기)이다.
- 국가는 요청한 국가나 `null`(전 세계)만 쓸 수 있다.
- 해석할 수 없는 ref는 버린다.

```python
resolve_evidence(refs: list[EvidenceRef], allowed_countries: set[str | None]) -> list[Evidence]
```

| metric | key | 값을 가져오는 TrendSummary 필드 |
|---|---|---|
| `topic_share` | Topic | `topics[]` |
| `work_topic_share` | Topic | `work_topics[]` |
| `work_share` | null | `work_share`. 업무 메시지(work_related=1)의 비중 |
| `work_intent` | asking/doing/expressing | `work_intent[]` |
| `usage_rank` | null | `usage_rank`. `from`/`to`는 분기 시작 월. 전 세계(null)는 불가 |

## 타입
```ts
Topic = "Writing" | "Practical Guidance" | "Seeking information" | "Technical help"
      | "Multimedia" | "Self-expression" | "Other/Unknown"   // 원본 값 그대로. 한국어 라벨은 프론트에서 붙인다
AskDoExpress = "asking" | "doing" | "expressing"
Month = string  // "YYYY-MM"

TrendsMeta = {
  months: { from: Month, to: Month },            // 현재 2024-07 ~ 2026-06
  countries: string[],                           // 지원 국가 (위 규칙)
  topics: Topic[],
  source: { name: "OpenAI Signals v2.0", license: "CC BY 4.0", url: string }
}

TrendSeries = {
  dimension: "topic" | "work_related" | "ask_do_express",
  country: string | null,                        // null = 전 세계
  work_related: 0 | 1 | null,
  points: { month: Month, key: string, share: number }[]   // share 0~1, 소수 3자리. 월·key 오름차순
}

TopicChange = { topic: Topic, from_share: number, to_share: number, change_pp: number }  // change_pp: %p 차이, 소수 1자리

TrendSummary = {
  country: string | null,
  period: { from: Month, to: Month },
  topics: TopicChange[],                         // change_pp 내림차순 (위 = 증가, 아래 = 감소)
  work_topics: TopicChange[],                    // 업무 메시지 기준, 같은 정렬
  work_share: { from: number, to: number, change_pp: number },
  work_intent: { intent: AskDoExpress, from_share: number, to_share: number, change_pp: number }[],
  usage_rank: {                                  // 인구 대비 사용량 순위 (1 = 최고). 전 세계면 null
    quarter: Month, rank: number,                // 최신 분기
    previous_quarter: Month | null,              // period.from 이후 첫 분기. 최신 분기와 같으면 null
    previous_rank: number | null
  } | null
}

EvidenceRef = {
  metric: "topic_share" | "work_topic_share" | "work_share" | "work_intent" | "usage_rank",
  key: string | null,
  country: string | null
}

Evidence = EvidenceRef & {
  from: Month, to: Month,
  from_value: number | null,                     // share는 0~1, rank는 순위. 이전 값이 없으면 null
  to_value: number,
  change_pp: number | null,                      // share 지표만
  label: string                                  // 서버가 만든다. 예: "KR 메시지 중 Practical Guidance 23.2% → 34.1% (2024-07 → 2026-06)"
}
```

## 변경 이력
| 날짜 | 변경 | 작성자 |
|---|---|---|
| 2026-10-01 | 추가 | ktc-kiju-kang |
| 2026-10-01 | 데이터 저장을 DB에서 레포 CSV로 변경, 지원 국가 67개로 정정 (API 형태는 그대로) | ktc-kiju-kang |
