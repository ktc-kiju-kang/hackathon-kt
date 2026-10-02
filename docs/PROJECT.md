# KT Group AI Opportunity Radar

> 전 세계 AI 사용 데이터를 분석해 KT 그룹이 다음에 만들어야 할 AI 서비스를 찾아주는 에이전트

## 흐름

```
OpenAI Signals 데이터 → Trend 분석 → KT 그룹사 사업 매칭 → Opportunity 발굴 → Product·PoC 설계
```

단순 Q&A 챗봇이 아니라, 실제 데이터를 근거로 단계별 분석을 거쳐 실행 가능한 프로덕트 카드까지 만든다.

## 데이터: OpenAI Signals (확인 완료 2026-10-01)

| 항목 | 내용 |
|---|---|
| 출처 | https://openai.com/signals/data-download/ (페이지는 봇 차단, 파일은 CDN에서 직접 받을 수 있음) |
| 파일 | `https://cdn.openai.com/signals/data-download-csv.zip` (CSV 25개, ~1.2MB), 데이터 사전 `https://cdn.openai.com/signals/data-dictionary.pdf` |
| 라이선스 | **CC BY 4.0**: 상업적 이용 가능, 화면·자료에 출처 표기 필수 ("OpenAI Signals v2.0", Chatterji et al.) |
| 범위 | 2024-07 ~ 2026-06 월별, 파일에 따라 125~150개국, 매월 개인 계정 메시지 30만 건 표본, 차등 프라이버시 노이즈 적용. **앱이 지원하는 국가는 67개** (업무 메시지 데이터까지 24개월이 모두 있는 국가, `KR`·`US` 포함) |
| 제외 | **기업(Enterprise) 계정은 제외** → 업무 활용이 과소 집계됨. Codex 사용분도 없음 |

**주요 차원** (값은 모두 `share_of_messages` 0~1이거나 `rank`)
- `topic` 7개: Writing / Practical Guidance / Seeking information / Technical help / Multimedia / Self-expression / Other/Unknown
- `work_related` (0/1), `ask_do_express` (asking/doing/expressing), `work_schoolwork`
- `country` × `month` 조합, 연령·성별, 요금제(plan_type)
- **미국 한정** O*NET IWA(직무 활동) 166개 코드: 직무 단위로 가장 세밀함. 코드만 있으므로 이름은 O*NET 사전과 조인해야 함
- 별도 파일: `ai-job-transition-framework-data-download.zip` (직업 922개 × AI 영향 유형)

**한계와 대응**
- topic 분류가 7개로 거칠다 → "Cloud 장애 대응" 같은 세부 기회는 데이터에서 바로 나오지 않는다. **데이터는 트렌드의 근거**로만 쓰고, 세부 기회는 LLM이 KT 사업 정보와 결합해 추론한다. 화면에 근거(어떤 지표)와 추론을 구분해 표시한다.
- 세부 직무 신호가 필요하면 미국 O*NET IWA 데이터를 참고 지표로 쓴다.
- Enterprise Signals(https://openai.com/signals/enterprise-data/)는 리포트만 있고 CSV는 없다. 필요하면 정성 근거로 인용한다.

**한국(KR) 예시** (2024-07 → 2026-06)
- Technical help 17.4% → 4.1%, Practical Guidance 23.2% → 34.1%, Self-expression 3.8% → 10.2%
- 인구 대비 사용량 순위 57위(2025 Q1) → 25위(2026 Q2)

## KT 그룹사 데이터

공개 자료(IR·홈페이지)를 요약한 `backend/data/companies.json`: 그룹사 5개(KT, KT Cloud, KT DS, BC카드, KT Skylife) × 사업 영역·고객·보유 자산. 내부 데이터는 쓰지 않는다 (공개 저장소). 개인 결제·통화 기록 같은 개인정보를 쓰는 기회는 제안하지 않게 프롬프트에 적어 두었다.

## MVP 화면

1. **Trend Dashboard**: Signals 지표 시각화 (topic 추이, 업무 비중, ask/do/express, 국가 비교, KR 강조)
2. **Opportunity Radar**: 그룹사를 선택하면 트렌드와 사업을 매칭해 Opportunity 카드 목록을 보여줌 (근거 지표 + 추론)
3. **Product Generator**: Opportunity 하나를 골라 Product Card와 PoC 계획을 생성 (문제·타깃·가치·핵심 기능·Flow·데이터·아키텍처·MVP 범위)

단계별 에이전트는 **단계마다 LLM 1회씩 구조화 출력**으로 만든다 (`app/agent/structured.py`, ADR 0006). 각 단계의 진행이 SSE로 화면에 보인다.
- Radar: trend → match → opportunity (요청당 LLM 최대 6회)
- Product: design → poc (요청당 LLM 최대 3회)

## 구현 상태 (2026-10-02)

| 화면 | 이슈·PR | 상태 |
|---|---|---|
| `/trends` Trend Dashboard | #22 · #26 | 운영 배포 |
| `/radar` Opportunity Radar | #23 · #27 | 운영 배포, **실제 LLM 미확인** |
| `/product` Product Generator | #24 · #29 | 운영 배포, **실제 LLM 미확인** |

- `/agent` 채팅에서도 `get_ai_usage_trends` 도구로 트렌드를 물어볼 수 있다.
- 남은 일:
  - 실제 LLM으로 `evals.run_radar_eval`·`run_product_eval` 확인 (Gemini 무료 일일 한도 소진으로 보류)
  - 데모용 LLM 키 결정 (아래 "데모 준비")
  - 사용량 한도의 IP 판별 (`X-Forwarded-For` 첫 값은 클라이언트가 바꿀 수 있음)

## 데모 시나리오

KT Cloud 선택 → 관련 트렌드(Technical help·업무 활용 등) 추출 → KT Cloud 사업과 매칭 → "Cloud 장애 대응 자동화" 등의 Opportunity 제안 → 하나 선택 → CloudOps Agent Product Card와 PoC 생성

## 데모 준비
- **LLM 한도**: Gemini 무료(`gemini-3.8-flash`)는 프로젝트당 하루 20회다. radar 1회 = 3회, product 1회 = 2회라 전체 흐름을 4번쯤 돌리면 끝난다. 리허설 횟수까지 생각해 유료 키(Anthropic, Console에서 월 한도 설정)로 바꿀지 정한다. 바꾸면 Render 대시보드에서 `ANTHROPIC_API_KEY`를 넣거나 `LLM_PROVIDER`를 지정한다.
- **Render 깨우기**: 무료 플랜은 15분 미사용 시 잠든다. 시연 1~2분 전에 `/api/health`를 호출한다.
- **예비안**: 한도에 걸리면 `/product`의 "샘플로 보기"와 `/trends`(LLM 없음)로 흐름을 보여줄 수 있다.

## 주의

- LLM은 레포 설정을 따른다 (Claude, Gemini, 또는 OpenAI 호환 API를 키로 자동 선택). 4단계 생성은 왕복이 많으므로 비용 보호 한도(`AGENT_MAX_TURNS` 등) 안에서 끝나게 설계한다.
- 화면 하단 등 결과물에 "Data: OpenAI Signals v2.0 (CC BY 4.0)" 출처를 표기한다.
