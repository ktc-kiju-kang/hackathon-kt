# 개발 파이프라인 — 단계별 추천 모델과 스킬

> 확인일: **2026-10-08**. 사용자 제공 `pipeline_v2.drawio`의 단계에 대응한다.
> 이 문서는 **개발 보조 모델·스킬 추천**이다. 앱의 Radar/Product `LLM_PROVIDER` 설정, 실제 에이전트 모델, 설치 상태를 변경하지 않는다.
> SDLC 점수 개선의 작업·완료 증거는 [실행 가이드](SDLC-IMPROVEMENT.md), 팀의 승인·머지 규칙은 [TEAM.md](../CLAUDE.md#충돌-방지-규칙-세-사람이-같은-것을-동시에-고치지-않게)가 기준이다.
> 전체 단계에서 골라 쓰려면 [7절 선택 체크리스트](#7-전체-단계-스킬-선택-체크리스트)를 사용한다. draw.io의 **두 번째 페이지 `Skill Selection`**에도 같은 선택 코드를 넣었다.

## 1. 먼저 구분할 것

| 구분 | 예 | 의미 |
|---|---|---|
| 모델 | Claude Opus 5.5, Claude Sonnet 5, GPT-6 Astra | 작업을 추론·작성하는 엔진 |
| 설치형 스킬 | `brainstorming`, `writing-plans`, `grill-me` | 모델에 읽히는 작업 절차. 설치만으로 테스트·보안 검사가 실행되지 않음 |
| CLI 내장 기능 | Copilot CLI `/plan` | 구현 전 계획을 만드는 기능. `plan`이라는 외부 스킬을 설치한다는 뜻이 아님 |
| 저장소 스킬 | `new-issue`, `pr-check`, `handoff` | 이 프로젝트의 이슈·검증·배포 규칙을 적용하는 절차 |
| 에이전트 | `reviewer` | 리뷰 역할과 별도 실행 문맥. 스킬과 같은 종류가 아님 |
| 결정적 도구 | pytest, Vitest, ruff, CI, gitleaks | 실제 결과를 판정하는 검사. 모델의 “통과했다”는 답변으로 대체 불가 |

Copilot CLI 1.0.91 도움말에서 `/plan`, `/model`, `/skills`, `/subagents`를 확인했다. Claude Code·다른 CLI의 호출 문법까지 동일하다고 가정하지 않는다. `/plan`으로 계획 모드에 들어가 **`writing-plans`의 산출물 규칙을 적용**하면 되고, 같은 계획을 두 번 작성할 필요는 없다.

## 2. 추천 모델 정책

[GitHub 공식 모델 비교](https://docs.github.com/en/copilot/reference/ai-models/model-comparison)의 작업군을 참고한 **프로젝트용 추천안**이다. 이 저장소에서 모델 간 성능·비용 벤치마크를 한 결과는 아니다. 사용 가능 여부·가격은 계정·조직 정책과 실행 시점의 모델 선택 화면에서 확인한다.

| 코드 | 기본 추천 | 맡길 일·선택 이유 | 대체·상향 기준 |
|---|---|---|---|
| P · 계획 | **Claude Opus 5.5** | 모호한 요구 정리, 여러 제약을 연결한 설계·검토. 큰 결정을 내리는 제한된 구간에 사용 | 사용할 수 없으면 GPT-5.5 등 고성능 추론 모델. 단순한 요구 정리는 C로 충분 |
| C · 구현 | **Claude Sonnet 5** | 범위·계약이 정해진 frontend/backend 구현과 테스트 작성의 기본값 | GPT-6 Sol 대체. 여러 계층에 걸친 난제는 P 또는 R로 원인 분석을 맡김 |
| R · 독립 검토 | **GPT-6 Astra** | 구현 diff·계약·실행 증거를 함께 검토하고 복합 실패를 분석. Sonnet 구현과 다른 계열의 관점을 추가 | 사용 불가 시 Opus 5.5. 모델이 같아도 새 문맥에서 원문·테스트로 검토하며 독립성을 과장하지 않음 |
| L · 경량 정리 | **GPT-6 Luna** | 이미 확정된 이슈·로그·릴리스 결과 요약. 판정이나 위험 수용은 맡기지 않음 | Claude Haiku 4.5 또는 작업 규모에 맞는 Auto. 단순 집계는 LLM 없이 처리 |
| — · 모델 없음 | **CI·스크립트·사람** | 큐 순서, 체크 결과, 머지, 테스트 실행·종료 코드 판정 | 실패의 원인 분석이 필요할 때만 C/R 호출 |

고성능 모델을 모든 Worker에 배치하거나 여섯 개를 항상 띄우는 방식은 권장하지 않는다. **기본 1개 작업, 계약과 파일이 독립적일 때만 병렬화**한다. 같은 오류가 반복되면 무한 재시도 대신 재현·가설·검증 결과를 정리해 범위를 줄이거나 사람에게 판단을 요청한다. 재시도 횟수·비용 한도는 작업 시작 시 합의하며, 이 문서가 자동 한도를 설정하지 않는다.

## 3. Flow에 넣는 단계별 매핑

출처 표기: **S** = `obra/superpowers`, **G** = `mattpocock/skills`, **A** = `anthropics/skills`, **Y** = `DietrichGebert/ponytail`, **V** = `vercel-labs/agent-skills`, **D** = `supabase/agent-skills`, **B** = `trailofbits/skills`, **L** = 저장소 로컬, **CLI** = 내장 기능. 개인 세션에서 사용 가능하다는 사실과 팀 전체에 설치됐다는 사실은 다르다.

| Flow 노드 | 추천 모델 | 적용 스킬·절차 | 산출물·다음 단계 조건 |
|---|---|---|---|
| REQUIREMENT | P | `brainstorming` [S] 기본. 논점이 많거나 설계를 강하게 검증할 때 `grill-me` [G] | 사용자 문제·포함/제외·REQ·인수 기준, 사용자 확인. 모호한 부분을 구현자가 임의 결정하지 않음 |
| DESIGN | P | `/plan` [CLI] + `writing-plans` [S]. 요구가 미정이면 앞 단계로 복귀 | 계약·ADR 필요 여부·수정 파일·정확한 검증법·작업 의존성·되돌리기 |
| ISSUE QUEUE | L 또는 없음 | `new-issue` → `start-task` [L] | 승인받은 이슈, assignee·선행 이슈·worktree. 사용자 assign만으로 여러 Worker의 원자적 claim이 구현되는 것은 아님 |
| DEVELOPER WORKERS | C | **`ponytail` [Y] + `test-driven-development` [S]** 기본. `using-git-worktrees`·`executing-plans` [S], 작업에 맞는 구현 스킬은 아래 선택표. 독립 작업만 `dispatching-parallel-agents` [S] | 기존 구현 재사용→실패 재현→최소한의 완전한 구현→회귀 성공. 검증·보안·접근성은 생략하지 않음. `.claude/rules/` 준수 |
| PRE-MERGE VALIDATION | 검사에는 없음, 리뷰는 R | `verification-before-completion` [S], `pr-check`·`handoff` [L], `reviewer` 에이전트. 필요 시 `requesting-code-review` [S]의 증거 형식 적용 | 최신 SHA의 lint/type/test/build·충돌·관련 보안 결과, 지적 처리. 같은 리뷰를 중복 실행할 필요 없음 |
| READY_TO_MERGE | 없음 | 추가 스킬 불필요. [SDLC DoD](pipeline.md) | 필수 체크·최신 리뷰·차단 지적 해소. PR 참고 점수만으로 READY 판정 금지 |
| MERGE QUEUE | 없음 | 추가 스킬 불필요. 사람의 의존성·충돌·최신성 확인 | 의존 PR 먼저, 같은 우선순위는 접수 순으로 처리하는 절차안. GitHub Merge Queue 활성화 사실을 뜻하지 않음 |
| MERGE | **사람** | `finishing-a-development-branch` [S]는 선택지·정리 자료만 보조 | 사람이 한 건씩 머지. 다른 사람 브랜치의 충돌은 main merge로 해결하며 무단 rebase/force push 금지 |
| CI → DEPLOY → SMOKE | 없음, 로그 정리는 L | `handoff` 결과 [L], `verification-before-completion` [S] | main CI→`make ship` 머지 후 main 검사→`make serve` 스모크, 대상 SHA·경고/건너뜀 확인 |
| PASS/FAIL · REOPEN | 원인 분석 R, 상태 판정 없음 | `systematic-debugging`, `receiving-code-review` [S], 필요 시 `new-issue` [L] | 재현·원인/가설·조치·재검증. 자동 revert·자동 PR 종료 대신 승인 절차 적용 |
| ALL PR MERGED | 없음 | 추가 스킬 불필요 | 이번 릴리스 범위의 PR 집합·배포 SHA 고정. “열린 PR 0개”가 전역 완료를 뜻하지 않음 |
| FULL INTEGRATION TEST | 실행 없음, 테스트 작성 C | `webapp-testing` [A, 신규 후보], `test-driven-development` [S] | 로컬/mock 브라우저 통합·회귀와 실패 증거. 핵심 회귀는 머지 전에도 실행 |
| ACCEPTANCE VALIDATION | R은 근거 대조 보조, **사람 인수** | `verification-before-completion` [S] + [DEMO 기준](../templates/submission/GUIDE.md) | REQ별 실제 결과, 승인된 실제 LLM 결과, 5분·3주·내보내기·예비안 확인 |
| DONE | L은 보고서 정리만 | `verification-before-completion` [S] | 배포·인수·남은 위험·복구 정보를 기록. 칸반 Done이나 AI 답변만으로 완료 선언 금지 |

**기존 그림의 해석 보정:** 6 Workers는 확장 예시이지 현재 실행 중인 자동화가 아니다. 단일 Worker 머지는 이 저장소의 **사람 머지**로 바꾼다. Smoke는 merge 직후 독립적으로 도는 단계가 아니라 main CI·Deploy 뒤다. 전체 테스트가 뒤에 그려져 있어도 핵심 회귀·필수 보안 확인을 배포 후까지 미루지 않는다. 후반 단계는 최종 결합·운영 인수 확인이다.

### 루프에 적용할 스킬

| 루프 | 지침 | 재진입·종료 증거 |
|---|---|---|
| L1 모듈 실패 | `systematic-debugging` → `test-driven-development` | 동일 재현 실패→수정 후 통과, 기존 회귀 유지 |
| L2 CI·충돌 실패 | `pr-check` + 원인별 디버깅 | 최신 main·SHA의 필수 검사와 지적 처리. 반복 실패 시 자동 PR 종료하지 않고 재분할 여부 확인 |
| L3 다음 PR | 스킬·LLM 불필요 | 의존성·CI·리뷰를 다시 확인한 다음 사람이 머지 |
| L4 Smoke 실패 | `make serve`·`make status` 로그 + `systematic-debugging` | 실제 로컬 배포 상태·부분 실패를 확인하고 수정/revert PR. 복구는 새 배포·기능 확인까지 |
| L5 통합·인수 실패 | 브라우저 재현 + `new-issue` | 실패 기준·후속 담당·재검증. 요구 자체가 모호하면 `grill-me`/`brainstorming`으로 돌아가 합의 |

## 4. 실제 스킬 출처와 추천 범위

### 기존 스킬 우선 사용

아래 S 스킬은 현재 세션 목록과 [upstream skills 디렉터리](https://github.com/obra/superpowers/tree/main/skills)에서 이름을 확인했다. 신규로 비슷한 `skills/implement.md` 등을 만들 필요가 없다.

| 스킬 | 확인한 출처 | 사용 범위 |
|---|---|---|
| `brainstorming` | [S / SKILL.md](https://github.com/obra/superpowers/blob/main/skills/brainstorming/SKILL.md) | 요구·대안·설계 합의 |
| `writing-plans` | [S / SKILL.md](https://github.com/obra/superpowers/blob/main/skills/writing-plans/SKILL.md) | 승인된 요구를 파일·테스트·작업 단위로 구체화 |
| `using-git-worktrees` | [S / SKILL.md](https://github.com/obra/superpowers/blob/main/skills/using-git-worktrees/SKILL.md) | 병렬 변경 격리 |
| `test-driven-development` | [S / SKILL.md](https://github.com/obra/superpowers/blob/main/skills/test-driven-development/SKILL.md) | 실패부터 확인하는 구현 |
| `executing-plans` | [S / SKILL.md](https://github.com/obra/superpowers/blob/main/skills/executing-plans/SKILL.md) | 승인된 계획의 순차 실행·중간 확인 |
| `dispatching-parallel-agents` | [S / SKILL.md](https://github.com/obra/superpowers/blob/main/skills/dispatching-parallel-agents/SKILL.md) | 공유 상태 없는 독립 작업에 한정 |
| `systematic-debugging` | [S / SKILL.md](https://github.com/obra/superpowers/blob/main/skills/systematic-debugging/SKILL.md) | 수정 전 증거·원인 분석 |
| `requesting-code-review` / `receiving-code-review` | [요청](https://github.com/obra/superpowers/blob/main/skills/requesting-code-review/SKILL.md) / [수신](https://github.com/obra/superpowers/blob/main/skills/receiving-code-review/SKILL.md) | 검토 근거 전달·지적 사실 확인 |
| `verification-before-completion` | [S / SKILL.md](https://github.com/obra/superpowers/blob/main/skills/verification-before-completion/SKILL.md) | 완료 주장 전 실제 실행 결과 확인 |
| `finishing-a-development-branch` | [S / SKILL.md](https://github.com/obra/superpowers/blob/main/skills/finishing-a-development-branch/SKILL.md) | 검증 후 인계·정리. 팀의 사람 머지 규칙 우선 |

저장소 스킬은 [new-issue](../.claude/skills/new-issue/SKILL.md), [start-task](../.claude/skills/start-task/SKILL.md), [pr-check](../.claude/skills/pr-check/SKILL.md), [handoff](../.claude/skills/handoff/SKILL.md)를 재사용한다. 로컬 전용 `reviewer`는 [.claude/agents/reviewer.md](../.claude/agents/reviewer.md)에 정의돼 있다.

### 구현 기본: ponytail

**`ponytail` [Y]을 구현의 기본 원칙으로 추가한다.** [GitHub 원문](https://github.com/DietrichGebert/ponytail/blob/main/skills/ponytail/SKILL.md)과 [skills.sh](https://skills.sh/dietrichgebert/ponytail/ponytail)를 확인했고, 현재 사용자 설치본도 사용 가능하다. 설치본과 upstream의 문구가 다르므로 같은 버전이라고 주장하거나 자동 갱신하지 않는다.

적용 순서는 **정말 필요한가 → 기존 코드·패턴 재사용 → 표준 라이브러리/플랫폼 → 이미 설치된 의존성 → 최소 구현**이다. 한 구현뿐인 인터페이스·사용처 없는 설정·미래용 추상화를 늘리지 않되, 호출부·테스트·fixture까지 필요한 변경은 끝낸다. 버그는 모든 관련 호출 경로를 확인하고 근본 원인에서 고친다.

기본 강도는 `full`을 권장한다. 작은 변경을 이유로 입력 검증·오류 처리·보안·접근성·계약·필수 검증을 빼지 않는다. **Ponytail은 구현 범위를 줄이는 원칙이고 TDD는 정확성을 확인하는 절차**이므로 함께 사용한다. 일반 스킬의 최소 테스트 예시보다 이 저장소의 [SDLC 검증 범위](pipeline.md)가 우선이다.

### 구현 작업별 추가 후보

모두 상시 로드하지 않는다. **기본은 ponytail + TDD, 해당 작업의 기능 스킬만 추가**한다. 아래 신규 후보는 원문을 확인한 추천이지 설치·프로젝트 적용 완료가 아니다.

| 우선순위·상태 | 스킬·출처 | 이 프로젝트에서 쓸 때 | 구체적으로 남길 결과·주의 |
|---|---|---|---|
| 우선 재사용 · 저장소에 있음 | [add-endpoint](../.claude/skills/add-endpoint/SKILL.md) [L] | API 추가·백엔드와 프론트 연결 | 계약→Pydantic/router/service→프론트 타입·mock→정상/오류 테스트. 범용 FastAPI 스킬을 추가하는 것보다 팀 계약을 유지하기 좋음 |
| 우선 재사용 · 저장소에 있음 | [add-page](../.claude/skills/add-page/SKILL.md) [L] | 새 Next.js 화면·메뉴 | 라우트·기능 폴더·AppShell·메뉴 연결, 기존 경로 충돌 확인. 화면 하나 때문에 전역 구조를 개편하지 않음 |
| 우선 재사용 · 저장소에 있음 | [add-agent-tool](../.claude/skills/add-agent-tool/SKILL.md) [L] | AI 에이전트에 새 조회·계산 행동 | Pydantic 입력 제한·자동 등록·외부 실패 테스트·도구 사용/미사용 eval. 실제 LLM 호출은 승인 후 |
| TS 수정 시 · 현재 개인 세션에 있음 | `typescript` | `.ts`/`.tsx`의 타입·API 응답·상태 모델 변경 | 프로젝트 `strict`·계약과 맞는 타입, 불필요한 단언 제거. 배포 출처는 이번에 확인하지 않았으므로 팀 설치 명령은 제시하지 않음 |
| 추천 · 신규 후보 | [vercel-react-best-practices](https://github.com/vercel-labs/agent-skills/blob/main/skills/react-best-practices/SKILL.md) [V] | React 렌더링·비동기 요청·번들 크기 검토 | 차트/카드 렌더, 요청 waterfall 등 관련 규칙만 적용하고 개선 주장은 전후 측정으로 확인. Next.js에 백엔드 로직을 옮기거나 SWR·캐시를 무조건 추가하지 않음 |
| DB 작업 때 · 신규 후보 | [supabase-postgres-best-practices](https://github.com/supabase/agent-skills/blob/main/skills/supabase-postgres-best-practices/SKILL.md) [D] | SQL·스키마·마이그레이션·인덱스·RLS 변경 | 이전 앱 호환·행 접근·쿼리 계획·잠금 영향 검토. 공유 DB 직접 실행 금지. `service_role`은 RLS를 우회하므로 service 권한 체크가 별도로 필요 |
| 복잡한 경계값 때 · 신규 후보 | [property-based-testing](https://github.com/trailofbits/skills/blob/main/plugins/property-based-testing/skills/property-based-testing/SKILL.md) [B] | SSE 파서·정규화·캐시 키처럼 입력 공간이 큰 순수 로직 | 예: 같은 SSE 바이트열은 청크 분할 방식과 무관하게 같은 이벤트를 내야 한다. 실패 seed·축소된 반례를 회귀로 보존. Hypothesis/fast-check 도입은 별도 의존성 결정 |

로컬 스킬의 축약 검증 명령이나 실제 DB 호출 예시는 현재 [SDLC](pipeline.md)·[공유 DB 규칙](pipeline.md#문제가-생기면)과 함께 읽는다. 테스트는 격리 환경으로 고정하고, 공유 DB 쓰기·정리 작업이나 승인 없는 실비용 호출을 지침의 예시만 보고 실행하지 않는다.

**지금 추가하지 않을 것:** `solid`·`clean-code`를 기본 묶음에 모두 겹쳐 적용하기보다 구조 문제가 있는 리팩터링 때만 선택한다. `property-based-testing`도 단순 CRUD마다 도입하지 않는다. 예제 테스트로 충분하거나 의미 있는 불변식을 정할 수 없으면 기존 pytest·Vitest로 끝낸다.

**검색에서 제외한 오래된 후보:** `vercel-labs/next-skills`의 `next-best-practices`는 [공식 이전 안내](https://github.com/vercel-labs/next-skills)에 따라 더 이상 별도 스킬이 아니다. 이 프로젝트의 Next.js 16.3 계열에서는 `frontend/node_modules/next/dist/docs/`와 `frontend/AGENTS.md`를 우선한다. `trailofbits/skills`의 `static-analysis`는 단일 스킬이 아니라 CodeQL·Semgrep 등을 묶은 플러그인이므로 구현 기본 묶음에 넣지 않고 보안 도구 도입 시 따로 검토한다.

### 요구 심화·브라우저 검증 추천

| 추천 | 확인한 출처·특징 | 도입 시 주의 |
|---|---|---|
| `grill-me` [G] | [현재 upstream](https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md), [skills.sh](https://skills.sh/mattpocock/skills/grill-me). 결정의 빈틈을 질문으로 검증 | **현재 upstream은 `grilling` 호출 wrapper**다. 새 설치 시 [grilling](https://github.com/mattpocock/skills/blob/main/skills/productivity/grilling/SKILL.md)도 필요하다. 현재 세션의 `grill-me`와 upstream 버전이 같다고 가정하지 않음 |
| `webapp-testing` [A] | [공식 Anthropic 스킬](https://github.com/anthropics/skills/blob/main/skills/webapp-testing/SKILL.md), [skills.sh](https://skills.sh/anthropics/skills/webapp-testing). Python Playwright로 로컬 UI·콘솔·스크린샷 확인 | **현재 세션 미설치 후보**. Playwright·브라우저·서버 준비 필요. 기존 Vitest를 대체하지 않고 CI E2E가 자동 생기지도 않음 |

`grill-me`는 요구가 충분히 확정된 작은 수정마다 강제 인터뷰하는 용도가 아니다. `brainstorming`으로 합의된 부분은 반복하지 않고, 비용·범위·실패 조건처럼 미결정된 부분만 질문한다.

`webapp-testing`의 일반 예시에는 `networkidle` 대기가 있지만 이 앱은 SSE를 쓴다. 장기 연결의 네트워크 정적 상태만 기다리지 말고 **화면의 준비 상태·`done/error`·사용자 중지 결과**를 검증하도록 프로젝트 테스트에 맞춘다. 운영 API를 향하는 프리뷰로 고의 장애를 재현하지 않는다.

### 출처 신뢰 확인 기록

2026-10-08 조회값이다. 설치 수·별 수는 검색 보조 지표이지 보안성·적합성 보증이 아니다.

| 출처 | 확인한 스킬의 skills.sh 설치 표시 | GitHub 저장소 별 수 | 판단 |
|---|---:|---:|---|
| `obra/superpowers` | `brainstorming` 383.6K | 296,440 | 기존 절차와 겹치므로 재사용 우선 |
| `mattpocock/skills` | `grill-me` 1.3M | 279,851 | 실제 원본 경로·wrapper 의존까지 확인 |
| `anthropics/skills` | `webapp-testing` 172.0K | 180,072 | 공식 제공자 출처, 로컬 UI 탐색에 적합한 신규 후보 |
| `DietrichGebert/ponytail` | [ponytail](https://skills.sh/dietrichgebert/ponytail/ponytail) 74.1K | 157,735 | 사용자 설치 출처와 공개 원문 확인, 재설치 없이 구현 기본 원칙으로 반영 |
| `vercel-labs/agent-skills` | [vercel-react-best-practices](https://skills.sh/vercel-labs/agent-skills/vercel-react-best-practices) 778.2K | 32,059 | Vercel 제공 React/Next 성능 가이드, 저장소 구조에 맞는 규칙만 선택 |
| `supabase/agent-skills` | [supabase-postgres-best-practices](https://skills.sh/supabase/agent-skills/supabase-postgres-best-practices) 435.2K | 2,708 | Supabase 공식 DB 설계·성능 지침 |
| `trailofbits/skills` | [property-based-testing](https://skills.sh/trailofbits/skills/property-based-testing) 6.3K | 7,420 | 보안 전문 업체 제공, 실제 불변식과 도입 비용이 있을 때 선택 |

각 값은 해당 스킬 또는 저장소 전체의 조회값이며, 표에 없는 모든 스킬의 설치 수를 확인했다는 뜻은 아니다. 링크는 가변 `main`이므로 설치 시점에 원문·라이선스·변경 이력을 다시 읽고 사용한 버전/commit을 기록한다.

### 전체 단계 검색에서 추가 확인한 후보

2026-10-08 GitHub 원문·현재 디렉터리와 skills.sh를 대조했다. 아래 설치 수는 조회 시점의 표시값이며, 저장소 별 수는 위 출처 표의 동일 저장소 값을 참고한다. 스킬 이름을 발견한 것과 이 프로젝트에서 유효성을 검증한 것은 별개다.

| 후보·원문 | 단계·선택 이유 | 전제·한계 | skills.sh 설치 표시 |
|---|---|---|---:|
| [doc-coauthoring](https://github.com/anthropics/skills/blob/main/skills/doc-coauthoring/SKILL.md) [A] | 요구·PRD·설계 문서·운영 회고를 문맥 수집→구조화→독자 관점 확인으로 정리 | 신규 후보. 이미 충분한 문서를 다시 작성하지 않음. 새 문맥/에이전트 검토는 필요·비용을 확인하고, 비밀값·내부 자료를 외부로 보내지 않음 | [88.9K](https://skills.sh/anthropics/skills/doc-coauthoring) |
| [grill-with-docs](https://github.com/mattpocock/skills/blob/main/skills/engineering/grill-with-docs/SKILL.md) [G] | 설계 질문과 함께 도메인 용어·중요 결정을 기록 | 신규 후보. **`grilling` + `domain-modeling` 호출 wrapper**. [domain-modeling](https://github.com/mattpocock/skills/blob/main/skills/engineering/domain-modeling/SKILL.md)의 기본 `docs/adr/` 대신 이 저장소의 `docs/decisions/`를 사용하도록 맞춰야 함. 단순 변경에 ADR을 양산하지 않음 | [1.1M](https://skills.sh/mattpocock/skills/grill-with-docs) |
| [web-design-guidelines](https://github.com/vercel-labs/agent-skills/blob/main/skills/web-design-guidelines/SKILL.md) [V] | 구현·리뷰 단계의 접근성·포커스·폼·UI 동작 검토 | 현재 개인 세션에 있음. 최신 외부 가이드와 프로젝트 테마/컴포넌트 규칙을 함께 확인. 코드 검토는 실제 브라우저·키보드 인수를 대체하지 않음 | [709.3K](https://skills.sh/vercel-labs/agent-skills/web-design-guidelines) |
| [codeql](https://github.com/trailofbits/skills/blob/main/plugins/static-analysis/skills/codeql/SKILL.md) [B] | 함수·파일 사이 데이터 흐름을 추적하는 SAST 작업 | 신규 후보. CLI·분석 DB·쿼리·라이선스/권한 확인 필요. **먼저 GitHub default setup을 검토**하고, 수동 분석이 필요할 때만 스킬 추가. 추출 대상 0개나 분석 실패를 취약점 0건으로 취급하지 않음 | [7.8K](https://skills.sh/trailofbits/skills/codeql) |
| [semgrep](https://github.com/trailofbits/skills/blob/main/plugins/static-analysis/skills/semgrep/SKILL.md) [B] | 규칙 기반의 빠른 SAST·특정 패턴 점검 | 신규 후보. 도구·규칙·검사 대상·엔진·반출 범위를 승인 후 실행. OSS/Pro 분석 범위가 다르고 외부 규칙 다운로드·유료 조건을 확인. 승인 생략 워크플로는 이 저장소 기본 절차로 사용하지 않음 | [8.8K](https://skills.sh/trailofbits/skills/semgrep) |
| [mutation-testing](https://github.com/trailofbits/skills/blob/main/plugins/mutation-testing/skills/mutation-testing/SKILL.md) [B] | 테스트가 의도한 결함을 실제로 잡는지 고급 검증 | 신규·후순위 후보. 현재 upstream은 **mewt/muton 중심**이며 일반 coverage 스킬이 아님. 지원 언어·도구·실행 비용부터 확인하고 격리 사본의 좁은 범위에만. Timeout/Skipped는 검출 성공이 아님 | [3.8K](https://skills.sh/trailofbits/skills/mutation-testing) |

보안에는 우선 **CodeQL default setup**, 필요에 따라 `codeql` 수동 분석 또는 `semgrep`을 선택한다. 둘을 처음부터 모두 설치할 필요는 없다. SCA(`npm audit`·`pip-audit`)와 gitleaks는 별도의 실제 검사이며, 스킬 카탈로그에 이름을 넣는 것으로 도입되지 않는다.

## 5. 설치·적용은 별도 승인

이번 작업은 **추천을 문서·그림에 추가**한 것이며 설치·모델 설정·Agent 자동 실행은 하지 않는다. 이미 있는 스킬은 재설치하지 않는다. 새로 필요한 경우에만 [Skills CLI](https://skills.sh/)의 해당 버전 도움말을 확인하고 선택 설치한다.

```bash
# 신규 후보: 설치 전 원문·라이선스·실행 스크립트·대상 에이전트 확인
npx skills add anthropics/skills@webapp-testing

# 아래도 전부 설치하는 목록이 아니라 작업별 선택 후보
npx skills add vercel-labs/agent-skills@vercel-react-best-practices
npx skills add supabase/agent-skills@supabase-postgres-best-practices
npx skills add trailofbits/skills@property-based-testing
```

전체 단계 신규 후보도 필요한 **한 항목만** 선택 설치한다. 아래 명령은 제안이며 이번에 실행하지 않았다.

| 선택 항목 | 승인 후 설치 예시 |
|---|---|
| 문서 공동 작성 | `npx skills add anthropics/skills@doc-coauthoring` |
| 설계 질문+문서화 | `npx skills add mattpocock/skills --skill grill-with-docs --skill grilling --skill domain-modeling` |
| UI 가이드 | `npx skills add vercel-labs/agent-skills@web-design-guidelines` — 현재 개인 설치본은 재설치하지 않음 |
| CodeQL 수동 분석 | `npx skills add trailofbits/skills@codeql` |
| Semgrep 분석 | `npx skills add trailofbits/skills@semgrep` |
| 변이 테스트 | `npx skills add trailofbits/skills@mutation-testing` — mewt/muton 설치·실행과는 별개 |

`ponytail`은 현재 사용자 환경에 있어 재설치하지 않는다. 다른 팀원이 새로 도입할 때의 선택 명령은 `npx skills add DietrichGebert/ponytail@ponytail`이며, 설치 위치·원문 버전·권한을 먼저 확인한다. 로컬 `add-*` 스킬은 이미 저장소에 있으므로 별도 외부 패키지가 필요 없다.

G 스킬을 새로 설치할 때는 `grill-me`만 복사하지 말고 위에서 확인한 `grilling` 의존을 함께 선택한다. 프로젝트 단위와 개인 전역 설치 중 팀이 쓸 위치를 정하고, 자동 승인 `-y`나 전역 설치 `-g`를 기본으로 넣지 않는다.

도입 PR/기록에는 `출처·버전 / 대상 CLI·설치 위치 / 호출 방법 / 읽기·쓰기·네트워크 범위 / 의존 스킬·도구 / 승인 경계 / 작은 입력의 기대 산출물과 실제 결과`를 남긴다. 스킬의 외부 코드 실행·push·배포·병렬 에이전트 권유가 저장소의 승인 절차를 대체하지 않는다.

## 6. 최소 적용 순서

1. **요구 한 건:** P + `brainstorming`, 필요 시 `grill-me`로 미결정 조건을 닫는다.
2. **계획 한 건:** `/plan` + `writing-plans`로 계약·파일·실패/성공 테스트를 확정한다.
3. **구현 한 건:** C + **ponytail + TDD**·worktree 절차로 작은 PR을 준비한다. API/화면/AI 도구 중 해당 `add-*` 스킬을 선택하고 TS 수정 시 `typescript`를 적용한다. 성능·DB·불변식 후보는 해당 작업일 때만 검토한다. 처음부터 6개 Worker를 띄우지 않는다.
4. **리뷰 한 건:** R + `reviewer`/`handoff`로 최신 SHA·근거·미확인을 남기고 사람 머지·배포 확인으로 연결한다.
5. **검증 보완:** UI 자동 검증이 필요할 때 승인받아 `webapp-testing`을 평가하고, [T2 완료 조건](SDLC-IMPROVEMENT.md#테스트ai-품질--t1t5)과 연결한다.

각 단계의 품질은 모델이 아니라 **산출물과 실행 증거**로 판단한다. 이 흐름을 채택해도 SDLC 점수가 자동으로 100점이 되는 것은 아니다.

## 7. 전체 단계 스킬 선택 체크리스트

**선택 방법:** 작업에 필요한 항목의 `[ ]`를 `[x]`로 바꾸고 선택 코드·대상 작업·선택일을 기록한다. **체크는 사용 권고의 채택이지 설치·실행·검증 완료가 아니다.** 사용자 요청이 명확한 **IMP-01 ponytail만 선택 표시**했으며, 나머지는 추천이라도 미선택이다. 기존 팀의 필수 검증·리뷰·승인 규칙은 체크 여부와 무관하게 유지된다.

권장 시작 조합은 **REQ-01 → DES-01 → ISS-01 → IMP-01/02/03 → REV-01 → TST-01 → MRG-01 → DEP-01**이다. 장애가 생기면 OPS-01을 적용한다. 작업에 관계없는 인터뷰·문서·스킬 호출은 생략하고, 신규 후보는 실제 공백이 있는 단계에만 선택한다.

### ① 요구분석 — 추천 모델 P

- [ ] **REQ-01 · 권장:** `brainstorming` [S]. 사용자 문제·범위·대안·인수 기준을 합의한다. 이미 확정된 작은 수정은 새 인터뷰를 반복하지 않는다.
- [ ] **REQ-02 · 심화 대안:** `grill-me` [G]. 미결정 조건·모순·비용/실패 상황을 집중 질문한다. REQ-01에서 합의한 질문을 중복하지 않으며, 새 upstream 설치는 `grilling` 의존을 포함한다.
- [ ] **REQ-03 · 문서가 필요할 때:** `doc-coauthoring` [A]. PRD·제안서의 독자·근거·누락을 정리한다. 문서 출판·이슈 생성은 별도 승인한다.

### ② 설계·계획 — 추천 모델 P

- [ ] **DES-01 · 권장:** `/plan` [CLI] + `writing-plans` [S]. 수정 파일·계약·의존성·실패/성공 테스트를 하나의 계획으로 만든다. `/plan`은 설치형 스킬이 아니다.
- [ ] **DES-02 · 복잡한 설계:** `grill-with-docs` [G]. 용어·설계 결정을 질문하면서 기록한다. `grilling`·`domain-modeling` 의존과 `docs/decisions/` 경로를 확인한다. REQ-02와 같은 인터뷰를 두 번 돌리지 않는다.

### ③ 이슈·작업 배정 — 모델 L 또는 없음

- [ ] **ISS-01 · 기존 절차 권장:** `new-issue` → `start-task` [L]. 사용자 승인 후 이슈·assignee·선행 항목·worktree를 연결한다. 스킬은 분산 Worker의 원자적 claim 시스템이 아니다.

### ④ 구현 — 추천 모델 C

- [x] **IMP-01 · 사용자 요청으로 채택:** `ponytail` [Y]. 기존 코드·표준/설치된 도구를 먼저 쓰고 가장 작은 **완전한** 변경을 만든다. 검증·보안·접근성은 줄이지 않는다.
- [ ] **IMP-02 · 권장:** `test-driven-development` + `executing-plans` [S]. 실패부터 확인하고 승인된 단위별로 구현한다. 병렬 격리가 필요하면 `using-git-worktrees`; 독립 작업만 `dispatching-parallel-agents`.
- [ ] **IMP-03 · 기능에 맞춰 선택:** `add-endpoint` / `add-page` / `add-agent-tool` [L]. API·화면·AI 도구 중 해당되는 것만 적용한다. TS 수정은 현재 세션의 `typescript` 지침도 따른다.
- [ ] **IMP-04 · React 성능:** `vercel-react-best-practices` [V]. 관련 규칙과 전후 측정으로 렌더·요청·번들을 개선한다. 모든 항목에 캐시/의존성을 추가하지 않는다.
- [ ] **IMP-05 · DB 변경:** `supabase-postgres-best-practices` [D]. SQL·schema·인덱스·RLS·잠금·이전 앱 호환을 확인한다. 공유 DB 직접 실행은 금지한다.

### ⑤ 코드·UI 리뷰 — 추천 모델 R

- [ ] **REV-01 · 저장소 권장:** `reviewer` 에이전트 + `handoff`·`pr-check` [L]. 최신 SHA·실제 검증·지적 처리·충돌 근거를 남긴다.
- [ ] **REV-02 · 리뷰 전달 보완:** `requesting-code-review` / `receiving-code-review` [S]. 검토 문맥 전달과 지적 사실 확인에 사용한다. REV-01과 같은 리뷰를 중복 실행하지 않는다.
- [ ] **REV-03 · UI 변경:** `web-design-guidelines` [V]. 접근성·포커스·폼·동작을 검토하고 실제 브라우저 인수로 연결한다.

### ⑥ 정적 분석·보안 — 실제 검사는 도구, 해석 보조 R

- [ ] **SEC-01 · 우선 경로:** GitHub CodeQL default setup을 확인하고, 수동 심층 분석이 필요하면 `codeql` [B]. 관리자 승인·언어별 분석·추출 품질·실패/미검사 증거가 필요하다.
- [ ] **SEC-02 · 대안/보완:** `semgrep` [B]. 빠른 패턴 검사나 CodeQL로 다루지 못한 승인된 규칙에 사용한다. 스킬 호출·OSS 실행만으로 Pro의 파일 간 분석 범위를 주장하지 않는다.

### ⑦ 테스트·인수 — 작성 C, 독립 대조 R, 실행은 도구

- [ ] **TST-01 · 권장:** `verification-before-completion` [S]. 현재 SHA의 명령·대상 수·실제 결과를 보고 완료를 판정한다. 사람의 REQ 인수와 비용 승인된 LLM 평가를 대체하지 않는다.
- [ ] **TST-02 · 핵심 UI:** `webapp-testing` [A]. 로컬/mock에서 Radar→Product·내보내기·오류/중지를 확인한다. 운영 API를 고의로 실패시키지 않는다.
- [ ] **TST-03 · 불변식:** `property-based-testing` [B]. SSE 청크 분할·정규화·캐시 키 같은 의미 있는 성질을 넓은 입력에서 확인한다. 새 테스트 라이브러리는 승인 후 도입한다.
- [ ] **TST-04 · 고급·후순위:** `mutation-testing` [B]. 기본 회귀가 갖춰진 뒤 테스트의 결함 검출력을 확인한다. mewt/muton 지원·시간/비용·격리 범위를 먼저 검토한다.

### ⑧ 머지·릴리스 준비 — 사람 수행, 모델 없음

- [ ] **MRG-01 · 인계 보조:** `finishing-a-development-branch` [S]. 검증·남은 위험·정리 선택지를 전달한다. 큐 순서는 명시적 상태로 관리하고, 실제 머지는 사람이 한다.

### ⑨ 배포·스모크 — CI/스크립트, 정리 보조 L

- [ ] **DEP-01 · 저장소 권장:** `make serve`·`make status` 결과 [L] + 완료 증거 확인. main 머지 후 검사와 로컬 배포 스모크의 SHA·경고·기능 인수를 확인한다. 플랫폼별 즉시 배포 스킬로 이 파이프라인을 우회하지 않는다. (클라우드 배포는 2026-10-08에 정리됨).

### ⑩ 운영·장애·회고 — 원인 분석 R, 기록 정리 L

- [ ] **OPS-01 · 장애 때 권장:** `systematic-debugging` + `receiving-code-review` [S]. 재현·원인/가설·영향·수정/revert·재확인을 연결한다. 무한 재시도·자동 revert는 하지 않는다.
- [ ] **OPS-02 · 인수 문서:** `doc-coauthoring` [A]. 승인된 사실을 기반으로 runbook·회고·대체 담당 인계를 작성한다. 정기 감시·알림 수신·복구 실측은 별도 운영 장치로 확인한다.

**선택 기록:** `선택 코드 / 대상 기능·단계 / 선택자·일시 / 개인·팀 적용 범위 / 출처 버전 / 필요한 권한·비용 / 설치 승인 여부 / 검증 증거 위치`.

새 스킬을 선택해도 이 문서에서 원격 설치·관리자 설정·공유 DB 변경·배포를 자동 실행하지 않는다. 그림의 체크 표시는 시각적 선택란이며 실제 설정과 연동되지 않는다.

## 8. 단계별 notification 확인과 선택안

### 확인 결과 — 상태 표시는 있지만 단계별 외부 알람은 미구현

**2026-10-08, 로컬 `dfd18f5`의 저장소 설정·스크립트 기준**으로 확인했다. 개인 전역 CLI 설정·OS 알림 권한·GitHub 구독·외부 서비스 대시보드는 확인하지 않았고, 테스트 알림도 발송하지 않았다. 따라서 아래의 `없음`은 **검토한 저장소에 발송 코드/설정이 없음**이라는 뜻이며 사용자의 모든 기기에 알림이 없다는 단정은 아니다.

| 확인 대상 | 실제 구현 | 알림 관점의 한계 |
|---|---|---|
| [.claude/settings.json](../.claude/settings.json) | `SessionStart` → [session-context.sh](../scripts/session-context.sh), 브랜치·이슈·PR을 표준 출력 | `Notification`·`Stop` 등 알림 handler 없음. 시작 정보 주입이지 OS/팀 채널 알람 아님 |
| Copilot 저장소 hooks | `.github/hooks/`·`.copilot/` 아래 설정을 찾지 못함 | 개인 전역 설정·호스트의 기본 알림은 별도. Claude 이벤트 이름을 Copilot에도 그대로 적용하지 않음 |
| [PR Review](../.github/workflows/pr-review.yml)·[채점 코드](../scripts/pr_review_score.py) | PR 코멘트 생성/갱신과 `GITHUB_STEP_SUMMARY` 작성 | 구독자 수신을 보장하지 않음. 같은 코멘트의 PATCH가 매번 새 알림을 만든다고 가정하지 않음 |
| PR 코멘트/채점 실패 | 오류를 출력하거나 실패 요약을 시도. 스크립트는 보고 전용으로 종료 코드 0 | 실패가 있어도 job 성공일 수 있으므로 Actions 실패 알림만으로 보고 실패를 잡지 못함 |
| [CI](../.github/workflows/ci.yml)·[Security](../.github/workflows/security.yml) | 잡 성공/실패·검사 로그 | 별도 Slack/Teams/Discord/OS 발송 단계 없음. 수신 설정은 미확인 |
| [CI](../.github/workflows/ci.yml) · [Security](../.github/workflows/security.yml) | 잡 순서·timeout·warning/error | 단계별 발송 job/handler 없음. 클라우드 Deploy 워크플로는 정리됨 |

GitHub의 [공식 workflow 알림](https://docs.github.com/en/actions/concepts/workflows-and-actions/notifications-for-workflow-runs)은 사용자가 구독하면 자신이 트리거한 **workflow run 완료** 등을 알려주는 기능이다. 개별 job·요구분석·설계·모듈 작업의 모든 전환을 팀원 모두에게 전달하는 장치는 아니다.

### 단계별 누락과 권장 이벤트

다음 이벤트 이름은 **후속 구현용 제안**이다. 현재 hook이나 API가 이미 제공하는 이름으로 취급하지 않는다.

| 단계 | 현재 저장소에서 볼 수 있는 상태 | 추가할 알림·수신 대상 |
|---|---|---|
| 요구분석 | 대화·문서·이슈의 수동 기록 | 요구 확인 요청/완료 → 요청자·담당자 |
| 설계·계획 | 계획 문서·확인 답변 | 설계 승인 대기/변경/확정 → 담당자·영향받는 기능 |
| 이슈·배정 | GitHub assignee·칸반·세션 시작 출력 | claim 충돌/차단/인계 → 작업자·조정 담당 |
| 구현·모듈 테스트 | 로컬 명령·에이전트 응답, 모듈 완료의 명시적 알람 없음 | 완료/실패/사용자 입력 필요 → 해당 작업자 |
| 리뷰 | PR 점수 코멘트·잡 요약·수동 리뷰 | 리뷰 요청/차단 지적/최신성 상실/리포트 발행 실패 → 작성자·리뷰어 |
| 정적·보안 검사 | CI·Security 상태, 전용 SAST/SCA 완료 증거 없음 | 차단 발견/검사 실행 실패/미검사 → 담당자·보안 검토자 |
| 통합·인수 테스트 | 테스트 로그·수동 DEMO 기록 | 테스트 실패/인수 요청/완료 → 기능·시연 담당 |
| 머지 | GitHub PR 상태 | 머지 대기/머지 완료 → 사람이 정한 머지 수행자·배포 담당 |
| 배포·스모크 | `make serve`·`make status` 결과·CI 잡 로그 | 스모크 완료·실패·예상 밖 건너뜀 → 배포 담당 |
| 운영·회고 | 수동 health·작업 기록, 정기 외부 감시 미구현 | 장애/복구/후속 조치 기한 → 운영 주 담당·대체 담당 |

### 알림 정책 선택 — 아직 미선택·미연결

알림은 별도 LLM 스킬을 추가하기보다 **명시적인 단계 상태 + CLI hook/CI 발송 처리**로 구현하는 것이 적합하다. 스킬은 결과 형식을 정할 수 있지만, 지속적인 감시·발송·수신 확인을 대신하지 못한다.

- [ ] **NTF-01 · 단계마다 확인하려면 권장:** 각 단계의 최종 완료·승인 대기·실패/차단·복구를 알린다. 매 tool 호출이나 재시도마다 발송하지 않고 같은 작업의 중복 이벤트를 합친다.
- [ ] **NTF-02 · 저소음 대안:** 실패/차단·승인 필요·릴리스 최종 완료/복구만 푸시하고 나머지 완료는 요약 기록으로 남긴다. NTF-01과 기본 정책 중 하나를 선택한다.
- [ ] **CH-01 · 개인 작업:** OS 데스크톱 알림. 선택한 CLI 버전의 hook·OS 권한을 확인한다. 로컬 PC 종료·원격 작업·방해금지 모드에서는 알람이 안 보일 수 있다.
- [ ] **CH-02 · GitHub 기본:** 이메일/웹 알림을 사용자별로 설정한다. 새 발송 코드는 최소화할 수 있지만 단계별 알람 요구를 이것만으로 충족하지 못한다.
- [ ] **CH-03 · 팀 공유:** 팀이 승인한 Slack/Teams/Discord 등의 채널 하나를 정한다. 관리자·보존/반출 정책·수신자·webhook 자격증명 보관·발송 권한 확인 후 연결한다. URL/토큰은 문서·코드·로그에 넣지 않는다.

채널은 조합 가능하지만 팀 채널은 하나로 시작한다. 구현에 앞서 `정책 코드 / 채널 / 수신·대체 담당 / 소음·야간 정책 / 대상 단계 / 재시도 상한 / 실패 시 조치`를 결정한다.

### 구현 시 보장해야 할 경계

1. **단계 완료를 명시한다.** [Claude 공식 hook](https://code.claude.com/docs/en/hooks)의 `Stop`은 응답 종료, `SubagentStop`은 하위 에이전트 종료이며 요구·설계·인수 완료 인증이 아니다. `Notification`도 Claude가 보내는 알림 이벤트이지 임의의 SDLC 상태 전환 전체가 아니다. 단계 코드와 실제 결과·증거를 먼저 기록하고 이에 맞춰 발송한다.
2. **상태와 전달 결과를 분리한다.** `stage_status`와 `delivery_status`를 따로 남긴다. 알림 실패를 작업 성공으로 덮거나 작업 실패를 숨기지 않는다. 전송 오류는 제한된 재시도 후 기록·대체 담당 확인으로 처리하고, 알림 장애 때문에 자동 rollback하지 않는다.
3. **중복·오래된 실행을 구분한다.** 이슈/worktree·단계·시도·SHA·이벤트 ID로 중복을 막고, 취소·superseded·예상 밖 skip은 성공이 아닌 별도 상태로 보낸다. PR이 바뀐 뒤 옛 SHA의 완료가 최신 성공처럼 보이지 않게 한다.
4. **CI 실패 경로에서도 남긴다.** 선행 job 실패로 후행 job이 skip되는 경우까지 `needs` 결과를 모아 처리한다. 워크플로 취소·timeout 때도 최종 보고 가능 범위를 확인한다. 성공 경로만 보낸 뒤 “단계별 알림 완료”라고 하지 않는다.
5. **발송 권한을 격리한다.** 신뢰하지 않는 PR 코드·의존성 설치 환경에 팀 알림 webhook이나 쓰기 토큰을 주지 않는다. PR 제목·본문·로그는 외부 입력으로 취급하고 멘션·링크·길이를 제한한다.
6. **최소 메타데이터만 보낸다.** 프로젝트·단계·상태·이슈/PR·SHA·시각·공개 가능한 결과 URL·짧은 요약을 허용 목록으로 정한다. 소스 원문·프롬프트·키·사용자 IP·내부 데이터를 기본 payload에 넣지 않는다.

### 알림 인수 기준 — 실제 연결 후에만 확인

`발생→전송 성공→수신 확인`은 서로 다른 증거다. 모든 대상 단계에서 합성 성공·실패·승인 대기·중복·취소·timeout/skip·전송 실패를 승인된 테스트 채널로 확인하고, **원본 작업 결과가 그대로 보존되는지**도 확인한다. 발송 HTTP 성공만으로 사람이 수신·확인했다고 기록하지 않는다.

현재는 **설정/코드 점검 및 개선안 작성까지만 수행**했다. 알림 hook·발송 코드·채널·시크릿·정기 감시를 추가하지 않았으며, 단계별 수신 시험은 미실행이다. 실제 구현은 사용자 선택·권한 확인 후 별도 이슈/PR로 진행한다.
