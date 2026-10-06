# KT Group AI Opportunity Radar

> 전 세계 AI 사용 데이터를 분석해 KT 그룹이 다음에 만들어야 할 AI 서비스를 찾아주는 에이전트

## 흐름

```
OpenAI Signals 데이터 → Trend 분석 → KT 그룹사 사업 매칭 → Opportunity 발굴 → Product·PoC 설계
```

단순 Q&A 챗봇이 아니라, 실제 데이터를 근거로 단계별 분석을 거쳐 실행 가능한 프로덕트 카드까지 만든다.

## 사용자 문제와 MVP 범위

- **대상 사용자**: KT 그룹사의 사업·서비스 기획자. 공개 AI 활용 지표와 그룹사 자산을 따로 조사해 사업 아이디어와 PoC 초안으로 연결해야 하는 작업을 돕는다.
- **제공 가치**: 트렌드의 수치 근거, 사업과 연결한 AI 추론, 실행 검토용 Product Card를 한 흐름에서 확인한다. 기획 시간 절감률·매출 효과·사용자 만족도는 아직 측정하지 않았다.
- **포함**: 공개 데이터 조회, 그룹사별 기회 생성, PoC 설계, Markdown 내보내기, 장애 시 저장된 데모 결과, Radar 동일 요청 재사용.
- **제외**: 사내·개인정보 수집, 실제 업무 시스템 조작, 제안한 제품의 구현·자동 배포, 투자/사업성 보증, Radar·Product 결과의 영구 저장.

## 요구사항과 수용 기준

아래 ID는 문서·이슈·검증을 연결하기 위한 식별자다. **기능 구현 여부와 수용 기준 검증 완료 여부는 별개**이며, 현재 CI 연결은 [SDLC](SDLC.md#요구사항별-검증-연결), 사용자 시나리오 인수는 [리허설](DEMO.md#리허설-통과-기준)에 남긴다.

| ID | 요구사항 | 관찰 가능한 수용 기준 | 계약·이슈 |
|---|---|---|---|
| REQ-01 | 공개 Signals 트렌드 조회 | 지원 국가·기간으로 차트와 요약이 일치하고, 잘못된 조건은 계약의 404/422. 출처·기간·기업 계정 제외 한계를 설명 가능 | [trends](contracts/trends.md), #22 |
| REQ-02 | 그룹사에 맞는 근거 있는 기회 | KT Cloud·KR 요청이 계약 순서의 SSE로 끝나고 `1 ≤ 기회 수 ≤ count`. 모든 기회에 서버가 채운 근거가 1개 이상이며 AI 추론과 구분됨 | [radar](contracts/radar.md), #23 |
| REQ-03 | Product Card·PoC·내보내기 | 선택 기회가 Product에 연결되고 서버가 근거를 재검증. "3주 안에 PoC" 요청은 실제 결과도 3주 이내인지 대조. 복사·`.md`에 화면의 핵심 설계 내용이 보존됨 | [product](contracts/product.md), #24 |
| REQ-04 | 장애 시 시연 예비안 | 저장된 KT Cloud 기회 3건 중 하나에서 대응 Product로 이동 가능. 생성 시각·모델·예시 안내를 표시하고 실시간 생성과 혼동하지 않음 | [radar snapshot](contracts/radar.md#get-apiradarsnapshotcompany_id--v1-데모-예비안), #32 |
| REQ-05 | 비용·오류·중지 처리 | 캐시에 남은 만료 전 동일 Radar 요청은 `done.cached=true`로 재사용하며 LLM·한도 미사용. 오류 결과는 재사용하지 않음. 한도·끊김·중지 시 진행 표시가 끝나고 오류 또는 예비안이 안내됨 | [radar](contracts/radar.md), #66 → #67 |

REQ-03의 현재 eval은 입력이 3주여도 `max_weeks: 4`를 허용한다. 따라서 기존 eval 통과는 3주 요구 충족의 증거가 아니며, 기준 수정 전에는 수동으로 확인한다. 사용자 리허설 #32는 2026-10-06 확인 시 열려 있다.

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

## 구현 상태 (2026-10-06 확인)

| 화면 | 이슈·PR | 상태 |
|---|---|---|
| `/trends` Trend Dashboard | #22 · #26 | 운영 배포 |
| `/radar` Opportunity Radar | #23 · #27 | 운영 배포, 2026-10-02 실제 LLM 확인 (#31) |
| `/product` Product Generator | #24 · #29 | 운영 배포, 2026-10-02 실제 LLM 확인 (#31) |

- `/agent` 채팅에서도 `get_ai_usage_trends` 도구로 트렌드를 물어볼 수 있다.
- #67로 **Radar 동일 요청 6시간 재사용·서버 전체 일일 한도 150건**이 반영됐다. 공급자까지 포함한 캐시 키·실패 결과 제외·재시작 시 초기화는 [계약](contracts/radar.md)을 따른다. Product 결과 캐시는 없다.
- 확인한 운영 버전은 `ba5b896`(#67)이며 Deploy 4단계 성공, health `db: ok`, `llm: openai`다. [확인 기록](worklog/2026-10-06.md#sdlc-문서-보완을-위한-추가-확인). health의 `openai`만으로 실제 모델·Groq 잔여 한도까지 확인할 수는 없다.
- 남은 일:
  - 리허설 1회와 예비안 인수 기록 (#32)
  - 위 수용 기준에 맞춘 PoC 기간 평가 보완, 핵심 UI 자동 검증 등 [SDLC 개선 목록](SDLC.md#7-남은-개선과-종료-조건)
- **과거 실제 LLM 확인** (2026-10-02, Groq `openai/gpt-oss-120b`): eval radar 2/2, product 1/1. 화면과 같은 SSE로 radar(KT Cloud) 20초 → product 48초. 분당 토큰 제한 429는 재시도로 통과했다. 현재 커밋의 재실행 결과나 지연시간 보장은 아니다.

## 데모 시나리오

KT Cloud 선택 → 관련 트렌드(Technical help·업무 활용 등) 추출 → KT Cloud 사업과 매칭 → "Cloud 장애 대응 자동화" 등의 Opportunity 제안 → 하나 선택 → CloudOps Agent Product Card와 PoC 생성

## 데모 준비
시연 당일 체크리스트·순서·문제 대응은 **`docs/DEMO.md`**.

- **LLM**: 데모 기본안은 Groq 무료(`openai/gpt-oss-120b`)다. 2026-10-02 기록상 공급자 한도는 하루 1,000회·20만 토큰·분당 8,000토큰이었다. 계정·모델별 한도는 시연 전에 다시 확인하며, 이를 현재 보장치나 가능한 시연 횟수로 쓰지 않는다. **radar·product를 연달아 누르면 수십 초씩 기다릴 수 있다**. 앱 자체 일일 한도 150건과 공급자 한도는 별개이고, 시연 중 다른 사람이 같은 키로 eval을 돌리지 않는다.
  - Render 대시보드: `LLM_PROVIDER=openai`, `LLM_BASE_URL=https://api.groq.com/openai/v1`, `LLM_MODEL=openai/gpt-oss-120b`, `LLM_API_KEY=<Groq 키>`. 반영 뒤 `/api/health`의 `llm`이 `openai`인지 확인
  - 대체 공급자를 쓰려면 사용 가능한 키·모델·한도를 다시 확인하고 같은 수용 기준으로 리허설한다. 과거 무료 한도나 다른 공급자의 성공 기록으로 대체하지 않는다.
- **Render 깨우기**: 무료 플랜은 15분 미사용 시 잠들 수 있다. [체크리스트](DEMO.md)에 따라 시연 10분 전에 `/api/health`로 준비한다. 첫 요청 시간은 환경에 따라 달라진다.
- **예비안 (데모 스냅샷)**: Groq 장애·한도로 실시간 생성이 실패하면 `/radar`·`/product`의 오류 카드에 **"저장된 결과 보기"** 버튼이 나온다. 미리 실제 LLM으로 만든 KT Cloud 결과(기회 3건 + Product Card 3건, `backend/data/demo/kt-cloud.json`)를 "{날짜}에 {모델}로 미리 만든 결과"라는 안내와 함께 보여준다. 시연 시나리오는 이 스냅샷과 같은 **KT Cloud**로 한다.
  - 다시 만들기: `cd backend && .venv/bin/python -m evals.make_demo_snapshot --company kt-cloud --count 3` (실제 LLM 약 9회·3분, 커밋 전 내용 확인)
  - 그 밖의 예비: `/product`의 "샘플로 보기", `/trends`(LLM 없음)

## 주의

- LLM은 레포 설정을 따른다. Anthropic·Gemini 키로 자동 선택하거나 `LLM_PROVIDER`로 지정하며, OpenAI 호환 API는 공급자·URL·모델·키 설정이 필요하다. Radar 3단계와 Product 2단계는 재시도까지 포함해 각각의 호출 예산 안에서 실행한다.
- 화면 하단 등 결과물에 "Data: OpenAI Signals v2.0 (CC BY 4.0)" 출처를 표기한다.
