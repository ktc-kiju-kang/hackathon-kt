# 구조와 분업 규칙

> 결정 배경: `docs/decisions/0007-folder-structure.md`. 요약은 `CLAUDE.md`.

## 현재 구조
```
frontend/                        Next.js(App Router) + TS + Tailwind v4 + shadcn/ui
  src/app/<route>/page.tsx         화면(라우트) — 기능 담당자
  src/features/<feature>/          기능별 컴포넌트·api.ts(타입+호출+mock) — 기능 담당자
  src/components/ui/               shadcn 생성 컴포넌트 (공용)
  src/components/app-shell.tsx     좌측 사이드바 + 상단 헤더(h-12) 레이아웃 (공용)
  src/components/app-sidebar.tsx   메뉴 — MENU_GROUPS 배열에 항목 추가 (공용, 한 줄씩)
  src/components/                  그 밖의 공용 컴포넌트, providers.tsx
  src/lib/api-client.ts            공용 HTTP 클라이언트(request, isMock)
  src/app/layout.tsx, page.tsx     공용 (최소 수정)
backend/                         FastAPI
  app/routers/<feature>.py         엔드포인트 (자동 등록) — 기능 담당자
  app/services/<feature>.py        비즈니스 로직·DB 접근 — 기능 담당자
  app/schemas/<feature>.py         Pydantic 요청/응답 모델 — 기능 담당자
  app/main.py                      공용 (수정 불필요)
  app/core/                        공용 — config.py(설정), db.py(Supabase), quota.py(사용량 한도·client_ip)
  app/agent/                       AI 에이전트 엔진 (공용) — providers/ 어댑터, tools/<name>.py 도구(기능 담당자), loop.py,
                                   structured.py(구조화 출력·SSE)·stages.py(단계 실행: radar·product가 사용)
  data/                            공개 읽기 전용 정적 데이터 (Signals CSV·그룹사 JSON, 출처·라이선스 README 포함)
  evals/                           평가 — run_eval(채팅 에이전트) · run_radar_eval · run_product_eval,
                                   make_demo_snapshot(데모 예비안 생성 → data/demo/) (모두 실제 API 비용)
  tests/test_<feature>.py
database/                        Supabase Postgres
  migrations/NNNN_<설명>.sql       스키마 변경 (규칙: database/README.md)
  seed.sql
docs/contracts/<feature>.md      기능별 API 계약
docs/decisions/                  ADR (0006: 정적 데이터·구조화 생성, 0007: 폴더 구조)
docs/worklog/YYYY-MM-DD.md       날짜별 작업 기록 (머지된 PR, 결정, 겪은 문제·교훈, 남은 일)
```

## 목표 구조와 분업 규칙 (ADR 0007 — `core/` 이동은 완료, `features/` 이동 전까지 위 "현재 구조"가 코드의 실제 모양)
```
backend/app/
  core/               공용 — config, db, quota (이동 완료, 이슈 #45)
  agent/              AI 엔진 — 공용 (tools/<name>.py 도구만 기능 담당자)
  features/<feature>/ 기능 담당자만 — router.py, service.py, schemas.py
frontend/src/
  features/<feature>/ 기능 담당자만 (이미 이 모양)
  components/, lib/   공용
```
- **지금 backend 새 기능은 현재 구조(`routers`·`services`·`schemas`)로 만든다.** 라우터 자동 등록이 `routers/`만 스캔해서 `app/features/`에 만들면 등록되지 않는다. 이동은 후속 이슈(진행 중 PR과 충돌하므로 열린 이슈 머지 후, 한 PR로).
- **이름 규칙**: 기능 이름은 backend 폴더·frontend `features/`·`docs/contracts/`·`tests/test_<f>.py`·API 경로에서 모두 같다. 한 개념에 이름 둘, 다른 개념에 같은 이름을 쓰지 않는다. (chat은 정리됨: backend `chat` = frontend `features/chat`, 화면 URL만 `/agent` — ADR 0007)
- **import 방향**: `features → core, agent`만. `core`는 다른 폴더를 import하지 않는다. `agent`는 `core`만 import한다 (단 `agent/tools/<name>.py`는 기능을 호출하는 도구라 해당 기능의 service를 import할 수 있다). **features끼리 직접 import 금지.** 알려진 예외(잠정): backend radar·product → `trends`(service와 schemas 모두), 도구 `get_ai_usage_trends` → `trends`, frontend product → radar(`Opportunity` 타입·선택 저장). 새 예외가 필요하면 만들기 전에 계약·ADR에 이유를 적고 리뷰를 요청한다.
- **새 공용 코드를 기능 폴더에 두지 않는다.** 둘 이상의 기능이 쓰면 공용 영역(`core`·`agent`·`components`·`lib`)에 별도 PR로 먼저 올린다. 이름도 실제 사용처를 따른다 (예: 여러 기능이 쓰는 한도를 `chat_*`라 부르지 않는다).
