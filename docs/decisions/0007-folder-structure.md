# 0007. 분업용 폴더 구조 (공용/기능 경계·import 방향)

- 상태: 채택(이름·소유·import 방향 규칙, 지금부터 적용) / 제안(폴더 이동 — 후속 이슈, 아래 미결 3건 확정 후)
- 날짜: 2026-10-02
- 결정자: 팀 (이슈 #36)

## 배경
3명이 "이슈(기능) 하나를 frontend + backend + DB까지" 맡는 구조다. 담당 범위가 폴더 경계와 맞고, 공용 영역이 폴더로 구분돼야 서로 같은 파일을 고치지 않는다.

현재 구조를 코드와 git 이력으로 확인한 결과:
- frontend는 이미 기능 폴더(`src/features/<feature>/`)다.
- backend는 레이어 폴더(`routers/` · `services/` · `schemas/`)라 기능 하나(예: radar)가 backend 4곳(routers·services·schemas·tests) + contracts + frontend 폴더 + 라우트 = **7곳**에 흩어진다.
- 지금 충돌을 만들고 있지는 않다. 코드 중 반복 수정이 잦은 파일은 `config.py`(7회)·`app-sidebar.tsx`(6회)·`services/health.py`(6회)뿐이고, 실제로 머지 충돌이 난 코드 파일은 `app-sidebar.tsx` 하나였다. 따라서 폴더 이동의 이득은 충돌 감소가 아니라 **담당 범위 = 폴더** 가 되는 것(찾기 쉬움)이다.
- "공용은 작게·별도 PR, 기능은 담당자만"이라는 경계가 문서에만 있고 폴더에는 없다. 예: `services/` 안에 기능 서비스와 공용(`rate_limit.py`·`chat_store.py`)이 섞여 있고, `check_chat_quota`는 이름은 chat인데 radar·product도 호출한다. `agent/structured.py`는 radar·product 전용 헬퍼인데 agent 엔진 폴더에 있다.
- 같은 개념에 이름이 둘이다: backend `chat`(= AI 에이전트 대화 API)을 frontend `features/agent`가 호출하고, frontend `features/chat`은 backend 연동이 없는 임시 mock 화면이다.

## 결정

### 1. 목표 구조
```
backend/app/
  main.py
  core/                    공용 — 변경은 별도 PR, 리뷰 권장
    config.py  db.py  quota.py        (quota = 현재 services/rate_limit.py)
  agent/                   AI 엔진 — 공용
    loop.py  providers/  prompts.py  types.py  errors.py
    (단계 실행 module — 이슈 #35 결과물)
    tools/<name>.py        도구 파일은 기능 담당자
  features/<feature>/      기능 담당자만
    router.py  service.py  schemas.py
backend/tests/test_<feature>.py     (평면 유지)
backend/data/  backend/evals/       (현재 위치 유지)
docs/contracts/<feature>.md

frontend/src/
  app/<route>/page.tsx     얇은 조립 — 기능 담당자
  features/<feature>/      기능 담당자만 (api.ts + 화면 컴포넌트)
  components/              공용 — 별도 PR (app-shell, app-sidebar, ui/)
  lib/                     공용 (api-client, utils, sse.ts — 이슈 #34)
```

### 2. 이름 규칙 — 한 개념 = 한 이름
기능 이름은 `backend/app/features/<f>` = `frontend/src/features/<f>` = `docs/contracts/<f>.md` = `tests/test_<f>.py` = API 경로 `/api/<f>`에서 모두 같다. 이름이 어긋나는 현재 항목은 이동 계획에 기록한다(아래).

### 3. 소유 규칙
- **공용**: `backend/app/core/`, `backend/app/agent/`(`tools/<name>.py` 제외), `frontend/src/components/`, `frontend/src/lib/`, 루트 설정. 작게 고치고 별도 PR로 먼저 머지, 리뷰 권장 (협업 규칙 5).
- **기능**: `features/<feature>/`(backend·frontend), `app/<route>/`, 해당 `contracts`·`tests`. 담당자(이슈 assignee)만 고친다 (협업 규칙 6).

### 4. import 방향
- backend: `features → core, agent` 허용. `core`는 다른 폴더를 import하지 않는다. `agent`는 `core`만 import한다(예외: `agent/tools/<name>.py`는 기능을 호출하는 도구라 해당 기능의 service를 import할 수 있다).
- **features끼리 직접 import 금지.** 알려진 예외(잠정, 아래 미결 1):
  - backend: radar → trends, product → trends (service와 schemas의 `Evidence`·`EvidenceRef` 모두), 도구 `get_ai_usage_trends` → trends (trends는 "데이터 제공 기능")
  - frontend: product → radar (`Opportunity`·`Evidence` 타입, 선택한 기회 저장 — radar 산출물을 이어받는 흐름)
- frontend: `app/<route>` → `features/*`, `components`, `lib` 허용. `lib`와 `components/ui`는 `features`를 import하지 않는다.

### 5. 이동은 후속 이슈로, 순서가 있다
라우터 자동 등록(`app/routers/__init__.py`)이 `routers/*.py`만 스캔하므로 **이동 전까지 새 backend 기능은 현재 구조(`routers`·`services`·`schemas`)로 만든다.** 지금부터 적용되는 것은 위 2~4의 규칙이다.

폴더 이동 순서 (진행 중 이슈와의 충돌 회피 — "큰 변경은 별도 PR로 먼저 머지"):
1. 이 문서(규칙 정의) — 코드 이동 없음.
2. 열린 이슈(#33·#34·#35 등) 머지 후: chat↔agent 이름 정리 → `core/` 분리(`config`·`db`·`rate_limit`→`quota`).
3. 마지막에 한 PR로: `features/<feature>/`로 기능 폴더 이동 + 자동 등록 스캔 경로 변경. 팀에 공지하고 이동 중에는 해당 파일 수정 금지. `/add-endpoint`·`/add-agent-tool`·reviewer·CLAUDE.md·ADR 0002의 경로 표기를 같은 PR에서 고친다.

## 대안
- **레이어 구조 유지**: 지금 충돌이 없어 이동 비용이 이득보다 클 수 있다. 다만 frontend와 지도(기능 폴더)가 달라 담당자가 두 가지 구조를 써야 한다 → 규칙 정의는 하되 이동 시점을 뒤로 미뤘다.
- **tests도 `tests/features/<f>/`로 이동**: 기능별 파일명이 이미 `test_<f>.py`라 이득이 작고, 같은 파일명이 여러 폴더에 생기면 pytest 모듈 이름 충돌 설정이 필요하다 → 평면 유지.
- **메뉴 항목을 기능 폴더가 소유(`features/<f>/menu.ts`)**: Next.js는 자동 수집이 없어 `app-sidebar.tsx`의 import 줄이 남으므로 충돌이 0이 되지 않는다(같은 줄 → import 줄로 약화) → 보류. 팀이 3명이라 충돌 해결 비용이 작으면 "메뉴는 항목 한 줄 추가" 규칙으로 둔다.

## 결과 / 트레이드오프
- 규칙은 즉시 효력이 있지만 폴더는 이동 전까지 현재 구조라, 문서(목표)와 코드(현재)가 한동안 다르다. CLAUDE.md에서 "현재 구조"와 "목표 구조"를 나눠 표시한다.
- ADR 0002의 "routers/services/schemas 계층" 표기는 이동이 끝날 때 이 문서가 대체한다 (이동 PR에서 0002에 반영).

## 미결 (정해지면 이 문서를 고친다)
1. **`trends` 처리**: radar·product·도구가 모두 쓰는 데이터 제공 기능이다. 공용 데이터 module로 승격할지(예: `app/data/trends`), 위 예외로 계속 둘지.
2. ~~**chat ↔ agent 이름**~~ — **결정·반영됨 (2026-10-02, 이슈 #44)**: API 경로 `/api/chat/...`와 화면 URL `/agent`는 유지하고, frontend `features/agent`를 `features/chat`으로 바꿔 backend 기능 이름 `chat`과 맞췄다. backend `app/agent/`(엔진)와의 이름 혼동도 없어졌다. 임시 mock 화면(`features/chat/ChatPanel`·`/chat`·메뉴 "채팅")은 삭제했다.
3. **quota 설정 이름**: `chat_rate_per_ip` 등 `CHAT_*` 환경변수가 radar·product도 제한한다. 이름을 `quota_*`로 바꾸려면 Render 대시보드 값 변경이 필요하다.
