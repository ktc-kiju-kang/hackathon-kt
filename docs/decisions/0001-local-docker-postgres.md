# 0001. 로컬 실행은 docker compose, DB는 PostgreSQL (실행·테스트·CI 전부)

- 상태: 채택
- 날짜: 2026-10-08
- 결정자: 팀 (레포 owner 결정, PR #92·#96·#97)

## 배경
- 본선은 서버 없이 **세 명이 각자 PC**에서 개발·실행·시험한다 (시작 키트 "로컬 우선" 결정).
- 그때까지 실행은 각 PC의 Python·Node를 직접 쓰고(`make dev`·`serve`), DB는 SQLite 파일(`backend/data/app.db`)이었다.
- 바라는 것: 세 PC에서 같은 방식으로 뜨는 실행 환경, 실제 서비스에 가까운 DB, 그리고 테스트가 그 DB를 그대로 검증하는 것.

## 결정
1. **실행 = docker compose** (`compose.yaml` + 개발용 `compose.dev.yaml`)
   - `make dev`: 소스 마운트 + 핫 리로드, Ctrl+C로 컨테이너까지 종료. `make serve`: 프로덕션 빌드 + 스모크.
   - 포트는 모두 `127.0.0.1`에만 연다 (행사장 네트워크에서 남이 붙어 LLM 비용을 쓰지 못하게).
   - `NATIVE=1 make dev`/`serve`로 docker 없이 기존 방식도 쓸 수 있다.
2. **DB = PostgreSQL 17** (compose `db` 서비스, 호스트 포트 **55432**, 데이터는 docker volume `pgdata`)
   - 드라이버 psycopg 3, 행은 dict(`row["컬럼"]`), 자리표시자 `%s`·`%(name)s`.
   - 접속 `DATABASE_URL`(기본 `postgresql://app:app@localhost:55432/app` — 로컬 전용 계정), 테이블 위치 `DATABASE_SCHEMA`.
3. **테스트도 PostgreSQL** — SQLite와 섞어 쓰지 않는다
   - pytest는 테스트마다 새 schema(`test_<랜덤>`)를 만들고 끝나면 지운다.
   - `make e2e`는 `e2e_<포트>` schema (worktree 두 곳이 동시에 돌려도 안 부딪힘).
   - `make verify`·`e2e`·`dev`·`serve`가 DB를 자동으로 띄운다 (`scripts/lib.sh`의 `ensure_db`). CI는 `services: postgres`.
4. **검사·시험·ship은 docker 안에서 돌리지 않는다** — `make verify`·`e2e`·`ship`은 CI와 같은 로컬 도구로 돌고 DB만 docker를 쓴다.

## 대안
| 대안 | 버린 이유 |
|---|---|
| 실행만 PostgreSQL, 테스트는 SQLite | SQL 문법이 둘(`?` vs `%s`, autoincrement vs identity, 날짜·JSON 타입)이라 코드가 복잡해지고, 테스트가 실제 DB를 검증하지 못한다 |
| 검사·시험까지 전부 docker 안에서 | 팀원 PC에 Python·Node가 없어도 되지만, `make ship`(gh·claude CLI)·CI와 경로가 달라져 손볼 곳이 많다. 시간 대비 이득이 작다 |
| SQLite 유지 | 설치가 가장 쉽지만, 실제 서비스에 가까운 DB에서 시험하자는 팀 결정과 맞지 않는다 |
| 호스트 포트 5432 | 개발 PC에 흔히 이미 PostgreSQL이 떠 있다 (실제로 레포 owner PC에서 Homebrew PostgreSQL과 다른 프로젝트 컨테이너가 5432를 쓰고 있었다) |

## 결과 / 트레이드오프
- 좋아진 것
  - 세 PC가 같은 이미지로 뜬다.
  - 테스트와 e2e가 실제 PostgreSQL을 검증한다 (pytest 58개 약 2초).
  - 앱 데이터(`public`)와 테스트 데이터가 schema로 분리된다.
- 치르는 비용
  - 모든 PC에 **Docker Desktop + `make setup`**(Python·Node)이 둘 다 필요하다.
  - `make verify`도 DB 때문에 Docker가 켜져 있어야 한다. CI는 Actions의 postgres 서비스를 쓴다.
  - 사내 GHE 러너가 `services:`를 지원하지 않으면 CI의 backend·e2e 잡이 돌지 않는다. 그 경우 로컬 `make verify`·`e2e` 결과를 PR 본문에 붙인다.
- 팀원 전환 (머지 후 한 번)
  - `git pull` → `make setup` (psycopg 설치) → Docker Desktop 켜고 `make dev`.
  - 옛 SQLite 데이터(`backend/data/app.db`)는 옮기지 않는다 (연습 데이터). 옛 `backend/.env`의 `DATABASE_PATH=`는 무시된다.
  - `0001_chat.sql`은 "적용된 마이그레이션 수정 금지" 규칙의 예외로 PostgreSQL 문법으로 다시 썼다. 엔진이 바뀌어 모든 PC가 빈 DB에서 시작하기 때문이다.
- 시험하며 찾은 함정 (코드에 반영됨)
  - **compose `env_file`이 `KEY=   # 주석`의 주석까지 값으로 읽는다** → `LLM_PROVIDER`가 깨져 health `llm=null`. 해결: `backend/.env`를 읽기 전용으로 마운트해 앱이 직접 읽게 했다.
  - **dev에서 `frontend/` 전체를 마운트하면 Tailwind가 `.next-e2e` 빌드 산출물(ANSI 로그)을 클래스 후보로 읽어 CSS가 깨진다**(화면 500). 컨테이너엔 `.gitignore`가 없기 때문이다. 해결: `frontend/src`만 마운트 (설정 파일을 바꾸면 `make dev` 재시작).
  - **PostgreSQL `text`·`jsonb`는 NUL(`\x00`)을 저장하지 못한다** (SQLite는 됐다). 대화 저장이 500·스트림 중단 → 저장 전에 제거 (`chat_store._no_nul`, 테스트 있음).
  - 마이그레이션은 서버 여러 개가 동시에 처음 떠도 한 번만 적용되도록 advisory lock 안에서 실행한다.
- 운영 메모: 명령·장애 대응은 `docs/pipeline.md`, DB 규칙은 `database/README.md`
  - `make db`: DB만 띄우기
  - `make db-reset`: 데이터 전부 삭제
  - 포트 충돌: `DB_PORT` + `DATABASE_URL`
