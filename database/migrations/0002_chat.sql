-- 0002: AI 에이전트 대화 저장 (docs/contracts/chat.md)
create table public.conversations (
  id uuid primary key default gen_random_uuid(),
  client_id text not null,           -- 로그인 없는 소유자 식별자 (브라우저 생성 UUID)
  title text,
  created_at timestamptz not null default now()
);
create index conversations_client_id_created_at_idx
  on public.conversations (client_id, created_at desc);
alter table public.conversations enable row level security;

create table public.messages (
  id bigint generated always as identity primary key,  -- 삽입 순서 = 대화 순서
  conversation_id uuid not null references public.conversations (id) on delete cascade,
  data jsonb not null,               -- app/agent/types.py Message (공급자 원본 raw 포함)
  created_at timestamptz not null default now()
);
create index messages_conversation_id_id_idx on public.messages (conversation_id, id);
alter table public.messages enable row level security;
