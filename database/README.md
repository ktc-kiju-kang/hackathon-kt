# database (PostgreSQL)

DB는 **백엔드(FastAPI)만** 접근한다. 각자 PC의 docker compose `db` 서비스(PostgreSQL 17, `127.0.0.1:55432`, 계정 app/app — 로컬 전용)를 쓴다. 팀원끼리 DB를 공유하지 않는다.

- 연결·마이그레이션 코드: `backend/app/core/db.py` (`get_db()`)
- 띄우기: `make db` (`make dev`·`serve`·`verify`·`e2e`는 알아서 띄운다). 접속 주소는 `DATABASE_URL`
- 연결 확인: `curl localhost:8000/api/health` → `"db":"ok"`
- schema: 앱은 `public`, `make e2e`는 `e2e`, 테스트(pytest)는 테스트마다 새 schema를 만들고 지운다 — 서로 섞이지 않는다.
- 처음부터 다시: `make db-reset` (DB 데이터를 지운다) → 서버를 다시 켜면 마이그레이션이 처음부터 적용된다.
- `schema_migrations`는 적용 기록용이다. 기능에서 읽거나 쓰지 않는다.

## 구성
```
migrations/YYYYMMDDHHMM_<설명>.sql   스키마 변경 (이름순으로 한 번씩 적용, 적용된 파일은 수정 금지 → 새 파일 추가)
```

## 규칙
- 테이블 변경 = 새 마이그레이션 파일 1개. 이름은 **만든 시각** `YYYYMMDDHHMM_<설명>.sql` (예: `202610141530_add_todos.sql`, `date +%Y%m%d%H%M`) — 세 사람이 동시에 만들어도 겹치지 않아 번호를 맞출 필요가 없다. `0001_chat.sql`은 키트 기본.
- **PostgreSQL 문법**으로 쓴다: 날짜는 `timestamptz`, JSON은 `jsonb`, 자동 번호는 `bigint generated always as identity`. schema 이름을 붙이지 않는다(`create table todos`, `public.todos` ✗) — 테스트·e2e가 schema로 격리한다.
- 이름은 snake_case. 기본 컬럼: `id text primary key`(uuid 문자열) 또는 `id bigint generated always as identity primary key`, `created_at timestamptz not null`.
- **행 접근 권한(누가 어떤 행을 볼 수 있는지)은 service 코드에서** 검사한다. RLS는 쓰지 않는다(앱이 한 계정으로 접속). 소유자 컬럼(예: `owner_id`, `client_id`)을 두고 모든 조회·수정에 조건을 건다 → `docs/security-compliance.md`에 코드 위치와 거부 시험을 남긴다.
- SQL에 값을 문자열로 이어 붙이지 않는다. 항상 `%s` 또는 `%(name)s` 자리표시자 (SQL 주입 방지).
- 확장(`create extension`)은 쓰지 않는다 — 테스트가 테스트마다 schema를 만들고 지우므로 확장이 한 schema에 묶여 사라진다. 꼭 필요하면 `create extension if not exists <이름> schema public` + `public.` 붙여 호출.
- 한 파일은 한 트랜잭션으로 적용된다. 파일 안에 `begin;`/`commit;`을 쓰지 않는다.
- 형식이 다르거나 SQL이 틀리면 서버가 시작하지 않는다 (`main.py` lifespan에서 적용).
- 각자 PC의 DB는 따로다 (docker volume `pgdata`). main에서 다른 사람의 마이그레이션이 들어오면 서버를 다시 켤 때 자동 적용된다 (`make sync`가 알려 준다).
- 기능별 테이블 스키마는 해당 기능 계약(`docs/contracts/<feature>.md`)과 `docs/arch.md` "데이터 모델"에도 적는다.
- 시험 데이터는 **합성 데이터**만 쓴다. 실제 개인정보를 넣지 않는다.
