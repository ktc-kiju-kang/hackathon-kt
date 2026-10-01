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
| 범위 | 2024-07 ~ 2026-06 월별, 135개국 (`KR` 포함), 매월 개인 계정 메시지 30만 건 표본, 차등 프라이버시 노이즈 적용 |
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

공개 자료(IR·홈페이지)를 요약해 정적 seed로 넣는다: 그룹사 5개(KT, KT Cloud, KT DS, BC카드, KT Skylife) × 사업 영역·고객·보유 자산. 내부 데이터는 쓰지 않는다 (공개 저장소).

## MVP 화면

1. **Trend Dashboard**: Signals 지표 시각화 (topic 추이, 업무 비중, ask/do/express, 국가 비교, KR 강조)
2. **Opportunity Radar**: 그룹사를 선택하면 트렌드와 사업을 매칭해 Opportunity 카드 목록을 보여줌 (근거 지표 + 추론)
3. **Product Generator**: Opportunity 하나를 골라 Product Card와 PoC 계획을 생성 (문제·타깃·가치·핵심 기능·Flow·데이터·아키텍처·MVP 범위)

단계별 에이전트(Trend → Matching → Opportunity → Product Designer)는 `app/agent/tools/`의 도구나 structured output 호출로 나눠 만든다. 각 단계의 진행 상황이 화면에 보이게 한다.

## 데모 시나리오

KT Cloud 선택 → 관련 트렌드(Technical help·업무 활용 등) 추출 → KT Cloud 사업과 매칭 → "Cloud 장애 대응 자동화" 등의 Opportunity 제안 → 하나 선택 → CloudOps Agent Product Card와 PoC 생성

## 주의

- LLM은 레포 설정을 따른다 (Claude, Gemini, 또는 OpenAI 호환 API를 키로 자동 선택). 4단계 생성은 왕복이 많으므로 비용 보호 한도(`AGENT_MAX_TURNS` 등) 안에서 끝나게 설계한다.
- 화면 하단 등 결과물에 "Data: OpenAI Signals v2.0 (CC BY 4.0)" 출처를 표기한다.
