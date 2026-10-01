# database (Supabase Postgres)

DB는 **백엔드(FastAPI)만** 접근한다. 프론트는 Supabase에 직접 붙지 않는다.

## 구성
```
migrations/NNNN_<설명>.sql   스키마 변경 (순서대로 적용, 적용된 파일은 수정 금지 → 새 파일 추가)
seed.sql                     데모/개발용 샘플 데이터
```

## 규칙
- 테이블 변경 = 새 마이그레이션 파일 1개. 번호 충돌을 피하려고 **PR 머지 직전에 번호를 확정**한다 (`ls migrations`로 마지막 번호 +1).
- 모든 테이블에 RLS를 켠다 (`alter table ... enable row level security;`). 백엔드는 `service_role` 키로 RLS를 우회하므로 정책 없이도 동작하고, anon 키로는 데이터가 열리지 않는다.
- 이름은 snake_case. 기본 컬럼: `id uuid primary key default gen_random_uuid()`, `created_at timestamptz not null default now()`.
- 기능별 테이블 스키마는 해당 기능 계약(`docs/contracts/<feature>.md`)에도 적는다.

- **이전 버전 backend와 호환되게 쓴다.** 마이그레이션이 backend 배포보다 먼저 적용된다.
  - OK: 테이블·nullable 컬럼·인덱스 추가
  - 2단계로: 컬럼 drop/rename → (1) 코드에서 사용 중단 배포 → (2) 다음 PR에서 drop
- 한 파일은 한 트랜잭션으로 적용된다. `create index concurrently`처럼 트랜잭션 밖에서만 되는 문은 쓰지 않는다.

## 적용 방법 (자동)
팀이 하나의 Supabase 클라우드 프로젝트를 공유한다. **main에 머지되면 Deploy 워크플로가 자동 적용**한다 (`scripts/migrate.sh`).
- 적용 기록: `public.schema_migrations(version, applied_at)`. 이미 기록된 파일은 건너뛴다.
- 실패하면 그 파일은 롤백되고 배포가 중단된다. 고친 내용은 **새 파일**로 올린다 (실패한 파일은 기록되지 않았으므로 같은 파일을 고쳐도 된다).
- 공유 DB에 SQL Editor로 직접 스키마를 바꾸지 않는다 (기록이 어긋난다).

### 로컬에서 미리 확인
```bash
docker run -d --rm --name pg -e POSTGRES_PASSWORD=pw -p 55432:5432 postgres:16-alpine
DATABASE_URL=postgres://postgres:pw@localhost:55432/postgres scripts/migrate.sh
docker stop pg
```
적용 예정 목록만 보기: `DATABASE_URL=<공유 DB> scripts/migrate.sh --dry-run`
