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

## 적용 방법
팀이 하나의 Supabase 클라우드 프로젝트를 공유한다.
1. Supabase 대시보드 > SQL Editor에서 새 마이그레이션 파일 내용을 실행
2. 또는 `psql "$DATABASE_URL" -f migrations/NNNN_xxx.sql` (Project Settings > Database > Connection string)

적용한 사람은 PR 코멘트에 "applied"를 남긴다. 공유 DB이므로 **파괴적 변경(drop, rename)은 팀에 먼저 알린다.**
