# SDLC — 단계별 작업 방식

> 이 프로젝트가 소프트웨어 개발 생명주기를 어떻게 돌리는지 한곳에 정리한다.
> **자동 강제**(도구가 막거나 대신 해 주는 것)와 **관례**(사람·Claude가 지키는 것)를 구분하고, **없는 것은 한계로 적는다.**
> 요약은 `CLAUDE.md`. 마지막 사실 확인: 2026-10-03.

## 1. 단계 맵

| 단계 | 이 프로젝트의 방식 | 산출물·도구 | 강제 |
|---|---|---|---|
| 요구사항·계획 | 이슈 하나 = 기능 하나. 템플릿에 목표·완료 조건·API 초안을 적고, 칸반 카드가 움직인다 (Todo·In Review·Done은 GitHub Projects 내장 워크플로로 자동 — 레포에 정의가 없고 설정은 `docs/TEAM.md`, In Progress만 `/start-task`) | `.github/ISSUE_TEMPLATE/`, `/new-issue`, 칸반, `docs/PROJECT.md`(주제·MVP·데모 시나리오) | 관례 (이슈 없이 시작 금지) |
| 설계 | **계약 우선** — API를 문서로 먼저 정한다. 되돌리기 어려운 결정은 ADR | `docs/contracts/`, `docs/decisions/`(0001~0007), `docs/architecture.md` | 관례 + reviewer 점검 항목 |
| 구현 | 브랜치 `<type>/<이슈번호>-…`, 기능 폴더, 작게 자주 머지 | `/start-task`, `/add-endpoint`·`/add-page`·`/add-agent-tool`, `.claude/rules/` | 관례 |
| 테스트 | 아래 3절 | pytest, Vitest, evals, ESLint, ruff, build | **CI가 강제** (evals 제외) |
| 리뷰 | PR 전 셀프 리뷰와 충돌 검사. 공용 파일·남의 기능·계약·마이그레이션은 리뷰 요청 | `reviewer` 에이전트, `/pr-check`, PR 템플릿 | 관례 (승인은 필수 아님) |
| 배포 | main 머지 → CI → migrate → backend → frontend → smoke | `.github/workflows/deploy.yml`, `docs/deploy.md` | **자동** |
| 운영·회고 | 상태는 `/api/health`, 배포는 `/deploy-status`, 날짜별 기록 | `docs/DEMO.md`(시연·장애), `docs/worklog/` | 관례 |

## 2. 완료의 정의 (Definition of Done)

이슈가 끝났다고 하려면 아래를 모두 만족한다.

1. 이슈의 **완료 조건**을 모두 충족했다 (이슈 본문 체크박스).
2. **계약 문서·pydantic 스키마·프론트 타입이 일치**한다. 계약이 바뀌면 영향받는 담당자를 리뷰어로 지정한다.
3. 변경한 쪽의 검증이 통과한다 — **CI가 강제** (`frontend`·`backend` 필수 체크).
4. `scripts/check-conflicts.sh`(`/pr-check`) 충돌 없음, `reviewer` 셀프 리뷰 완료 — 관례, PR 템플릿 체크리스트.
5. PR 본문에 `Closes #<이슈번호>` — 추적성. 머지하면 이슈가 닫히고 카드가 Done이 된다 (GitHub Projects 내장 워크플로, `docs/TEAM.md`).
6. 규칙·구조·계약에 영향이 있으면 **같은 PR에서 문서를 고친다**.
7. 머지 후 **배포를 확인**한다: Deploy 4단계 성공 + 운영 `/api/health`의 `version`이 머지 커밋과 같다 (`/deploy-status`). — 관례 (스모크 테스트는 자동).

**자동 강제되는 것** (2026-10-03 확인): `main`은 보호 브랜치이고 필수 상태 체크는 `frontend`·`backend` 두 개다 (비관리자에게 강제). 승인 리뷰는 필수가 아니고 관리자는 우회할 수 있다. 머지된 브랜치는 자동 삭제된다. 그 밖(이슈 선행, 계약 우선, 셀프 리뷰, 배포 확인)은 관례다.

## 3. 테스트 전략

| 계층 | 무엇을 | 위치 | 실행 | 비용 |
|---|---|---|---|---|
| 단위·API | pytest 88개 — 계약의 이벤트 순서, 입력 검증, 사용량 한도, 단계 파이프라인. DB·LLM 없이(mock·가짜 공급자) | `backend/tests/` | CI 자동 | 무료 |
| 단위 (frontend) | Vitest 14개 — `lib/sse.ts`(SSE 파서·스트림 읽기): 청크 분할, 끊김 감지, 서버 오류 문구, 헤더·취소 | `frontend/src/**/*.test.ts` | CI 자동 (`npm test`) | 무료 |
| 정적 검사 | ruff(lint·format), ESLint | CI | 자동 | 무료 |
| 비밀값 스캔 | gitleaks — 기본 규칙 + `.env.example`의 키처럼 긴 값 | `.gitleaks.toml`, `.github/workflows/security.yml` | PR·main push 자동 (**필수 체크는 아님**) | 무료 |
| 빌드 | Next.js build (타입 검사 포함) | CI | 자동 | 무료 |
| 품질 평가 | 실제 LLM으로 에이전트·radar·product 결과를 규칙으로 채점 | `backend/evals/` | **수동**, 실행 전 사용자 확인 | **실제 API 비용** |
| 스모크 | health·version·db·화면·CORS | `scripts/smoke.sh` | 배포 후 자동 | 무료 |

- **원칙**: 외부 의존(DB·LLM)은 테스트에서 고정한다. CI에는 DB도 LLM 키도 없고, 로컬 `.env`에 실제 키가 있어도 테스트 결과가 달라지면 안 된다.
- **한계 (솔직히)**:
  - 프론트 자동 테스트는 **`lib/sse.ts` 한 곳(14개)뿐**이다. 컴포넌트·화면 동작 테스트는 없어서 UI는 사람이 직접 확인한다.
  - 커버리지를 **측정하지 않는다**. E2E 테스트도 없다.
  - 품질 평가(evals)는 비용 때문에 CI에서 돌지 않는다.
  - **비밀값 스캔(`Security` 잡)은 필수 체크가 아니다.** 필수 지정에는 저장소 관리자 권한이 필요하다 (현재 필수는 `frontend`·`backend`). 알려진 키 형식과 `.env.example`의 긴 값만 잡으므로, 값 모양이 평범한 비밀값은 `reviewer` 점검 항목이 본다.
  - **Dependabot은 버전 업데이트 PR만 온다.** 저장소 설정에서 *Dependabot alerts*(취약점 경고)가 꺼져 있어(2026-10-03 API 확인) 취약점 기반 보안 업데이트는 오지 않는다. GitHub Secret scanning·Push protection도 관리자 설정이다.
  - 후속 후보: 컴포넌트 테스트(React Testing Library), 커버리지 기준선, 관리자 설정(필수 체크·Dependabot alerts·Secret scanning).

## 4. 추적성

```
이슈(목표·완료 조건) ←─ Closes #n ─ PR(변경·검증 체크리스트) ─→ 계약 문서 · ADR · 문서 변경
        └─ 커밋 `<type>(<feature>): 요약`                         └─ docs/worklog/ (머지된 PR·결정·교훈)
```

## 5. 되돌리기 (롤백)

- **자동 롤백은 없다** (ADR 0004). 문제가 생기면 **revert PR**을 머지하면 같은 파이프라인으로 되돌아간다.
- **DB 스키마는 되돌리지 않는다.** 그래서 마이그레이션은 이전 버전 코드와 호환되게 쓴다 (컬럼 추가 OK, drop·rename은 2단계).
- 배포 중 실패하면: migrate 실패 → 이후 단계 중단 / backend 실패 → frontend 배포 안 함 / frontend 실패 → 이전 버전 유지.

## 6. 장애 대응 (실제로 겪은 것 — 2026-10-02~03 작업 중 직접 만난 사례. 일부는 아직 `docs/worklog/`에 없다)

| 증상 | 원인 | 조치 |
|---|---|---|
| Deploy의 backend 단계가 `Wait for new version`에서 15분 뒤 실패 (2026-10-02, `4d1e84c`) | 워크플로가 15분 안에 새 버전을 확인하지 못함(Render가 새 커밋을 못 띄운 것으로 보이며, 원인은 Render 대시보드 로그에서만 볼 수 있다) | 그사이 main에 새 커밋이 있으면 **다음 Deploy가 처리**한다 (실제로 다음 커밋에서 해소). 계속 실패하면 Render 로그를 보고 수동 재배포(`gh workflow run deploy.yml`, 사용자 확인) |
| 운영 API 첫 요청이 응답이 없음(타임아웃) | Render free는 15분 미사용 시 잠든다 | `/api/health`를 반복 호출해 깨운다(약 1분). 시연 10분 전에 미리 |
| radar·product·agent가 429 | LLM 무료 한도(분당·일일) | radar "저장된 결과 보기"(`docs/DEMO.md`), 한도 확인 |
| 로컬 pytest가 `ModuleNotFoundError: anthropic` 등으로 수집 실패 | main에 의존성이 추가됐는데 로컬 venv가 낡음 | `.venv/bin/pip install -r requirements-dev.txt` |
| 로컬 build가 `.next/dev/types/… Cannot find module '…/page.js'`로 실패 | 삭제한 라우트를 가리키는 생성 캐시 | `rm -rf frontend/.next` (gitignore됨, CI에는 없음) |
| 테스트·`fastapi dev`가 실제 공유 DB에 붙음 | `backend/.env`에 실제 Supabase 키가 있음 | 테스트는 설정을 고정(monkeypatch). 수동 확인은 `SUPABASE_URL=` 등을 비워 실행하고, 쓴 데이터는 지운다 |
| Dependabot PR이 한꺼번에 열림 (설정 직후 첫 실행에 7개) | 첫 실행은 밀린 업데이트를 한 번에 만든다. 설정은 주 1회·그룹이지만 생태계마다 한도가 따로다 | CI 통과를 확인하고 **하나씩** 머지한다. GitHub Actions 메이저 업데이트(예: `checkout` 4→7)는 PR CI가 못 돌리는 `deploy.yml`에 영향이 있으니 머지 뒤 `Deploy`를 한 번 수동 실행해 확인한다 |
| 비밀값 스캔이 `.env.example`의 빈 값 줄(`KEY=`)에서 오탐 | gitleaks `generic-api-key`가 줄바꿈을 넘어 다음 줄을 값으로 잡는다 | `.gitleaks.toml`에 규칙 1개×경로 1개로 좁힌 예외가 있다. 새 오탐은 파일 통째가 아니라 같은 방식으로 최소 범위만 허용한다 |

더 많은 사례와 교훈은 `docs/worklog/`에 날짜별로 남긴다.
