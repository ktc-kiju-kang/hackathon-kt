# database (SQLite)

DB는 **백엔드(FastAPI)만** 접근한다. 외부 DB 서비스 없이 파일 하나(`backend/data/app.db`, gitignore)로 동작한다.

- 연결·마이그레이션 코드: `backend/app/core/db.py` (`get_db()`)
- 연결 확인: `curl localhost:8000/api/health` → `"db":"ok"`
- 처음부터 다시: 서버를 끄고 `rm backend/data/app.db` → 다시 켜면 마이그레이션이 처음부터 적용된다.
- `schema_migrations`는 적용 기록용이다. 기능에서 읽거나 쓰지 않는다.

## 구성
```
migrations/YYYYMMDDHHMM_<설명>.sql   스키마 변경 (이름순으로 한 번씩 적용, 적용된 파일은 수정 금지 → 새 파일 추가)
```

## 규칙
- 테이블 변경 = 새 마이그레이션 파일 1개. 이름은 **만든 시각** `YYYYMMDDHHMM_<설명>.sql` (예: `202610141530_add_todos.sql`, `date +%Y%m%d%H%M`) — 세 사람이 동시에 만들어도 겹치지 않아 번호를 맞출 필요가 없다. `0001_chat.sql`은 키트 기본.
- **SQLite 문법**으로 쓴다: `text`·`integer`·`real`, 날짜는 ISO 8601 문자열(`text`), JSON은 `text`. `uuid`·`jsonb`·`timestamptz`·RLS는 없다.
- 이름은 snake_case. 기본 컬럼: `id text primary key`(uuid 문자열) 또는 `id integer primary key autoincrement`, `created_at text not null`.
- **행 접근 권한(누가 어떤 행을 볼 수 있는지)은 service 코드에서** 검사한다. DB에는 권한 기능이 없다. 소유자 컬럼(예: `owner_id`, `client_id`)을 두고 모든 조회·수정에 조건을 건다 → `docs/security-compliance.md`에 코드 위치와 거부 시험을 남긴다.
- SQL에 값을 문자열로 이어 붙이지 않는다. 항상 `?` 또는 `:name` 자리표시자 (SQL 주입 방지).
- 한 파일은 한 트랜잭션으로 적용된다. 파일 안에 `begin;`/`commit;`을 쓰지 않는다.
- 형식이 다르거나 SQL이 틀리면 서버가 시작하지 않는다 (`main.py` lifespan에서 적용).
- 각자 PC의 DB는 따로다. main에서 다른 사람의 마이그레이션이 들어오면 서버를 다시 켤 때 자동 적용된다 (`make sync`가 알려 준다).
- 기능별 테이블 스키마는 해당 기능 계약(`docs/contracts/<feature>.md`)과 `docs/arch.md` "데이터 모델"에도 적는다.
- 시험 데이터는 **합성 데이터**만 쓴다. 실제 개인정보를 넣지 않는다.
