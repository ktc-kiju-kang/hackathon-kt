-- 0001: AI 에이전트 대화 저장 (docs/contracts/chat.md). SQLite 문법.
create table conversations (
  id text primary key,                -- uuid 문자열
  client_id text not null,            -- 로그인 없는 소유자 식별자 (브라우저 생성 UUID)
  title text,
  created_at text not null            -- ISO 8601 UTC
);
create index conversations_client_id_created_at_idx
  on conversations (client_id, created_at desc);

create table messages (
  id integer primary key autoincrement, -- 삽입 순서 = 대화 순서
  conversation_id text not null references conversations (id) on delete cascade,
  data text not null,                   -- app/agent/types.py Message JSON (공급자 원본 raw 포함)
  created_at text not null
);
create index messages_conversation_id_id_idx on messages (conversation_id, id);
