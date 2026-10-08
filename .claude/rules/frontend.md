---
paths:
  - "frontend/**"
---

# frontend 코드 규칙

> `frontend/**` 파일을 다룰 때 자동으로 로드된다. 구조·분업 규칙은 `CLAUDE.md`.

- 이 버전의 Next.js는 학습 데이터와 다를 수 있다. API·규칙이 애매하면 `frontend/node_modules/next/dist/docs/`를 먼저 확인한다 (`frontend/AGENTS.md`).
- 기본은 Server Component. 상태·이벤트·브라우저 API가 필요한 컴포넌트만 `'use client'`.
- 데이터·비즈니스 로직은 FastAPI에 둔다. Next.js Route Handler/Server Action에 백엔드 로직을 넣지 않는다.
- UI는 shadcn 컴포넌트 우선: `npx shadcn@latest add <이름>` → `src/components/ui/` (생성 코드 직접 수정 최소화).
- import는 `@/` 별칭, 클래스 병합은 `cn()` (`@/lib/utils`), 아이콘 `lucide-react`, 알림 `sonner`의 `toast`.
- 색상은 테마 토큰(`bg-background`, `text-muted-foreground` 등)만. 다크모드는 `next-themes`(시스템 연동).
  - 테마 토큰은 KDS 2.0 토큰에 연결돼 있다. 디자인 규칙(버튼·차트 색·그림자·KT Flow 금지)은 `.claude/rules/kds.md`.
  - **차트 계열 색**은 `var(--chart-1)`~`--chart-5`(KDS teal → yellow → blue → purple → red). 3색 이하로 쓰고 범례를 함께 둔다.
  - shadcn `ChartConfig`의 키는 CSS 변수 이름(`--color-<key>`)이 되므로 **영문만** 쓴다 (한글·공백 키는 선이 안 그려짐). 표시 이름은 `label`에.
- **API 호출은 `src/features/<feature>/api.ts`에서만**, `@/lib/api-client`의 `request` 사용. `isMock`일 때 계약 형태의 mock을 반환해 백엔드 없이도 동작하게 한다.
- effect 본문에서 setState를 동기 호출하지 않는다 (lint 에러). 비동기 콜백(`.then`)에서 호출한다. effect 콜백은 값을 반환하지 않게 `{ }`로 감싼다.
  - 선택이 바뀔 때마다 다시 불러오는 effect는 cleanup에서 이전 요청을 무시한다 (`let cancelled = false` → `return () => { cancelled = true }`). 늦게 온 이전 응답이 최신 결과를 덮지 않게.
  - `sessionStorage`·`localStorage`는 브라우저에서만 → effect 안에서 비동기로 읽고, 읽기·쓰기는 try/catch.
- **SSE를 읽는 클라이언트**(`features/chat/api.ts`): `done`·`error` 없이 스트림이 끝나면 연결 끊김으로 보고 오류를 던진다. 중지·오류 시 진행 중 표시(스피너)를 끈다. `AbortController`로 취소한다.
- **순수 로직의 테스트**(`lib/`, `features/*/api.ts`의 파서·변환 등)는 `*.test.ts`로 둔다 — Vitest, `npm test`, CI가 실행한다 (예: `src/lib/sse.test.ts`). 화면(컴포넌트) 테스트는 아직 없다. Vitest 5.x는 Node 22.12+를 요구해 CI의 Node 20과 맞지 않으므로 4.x를 쓴다.
- LLM이 만든 문자열을 React `key`로 쓸 때는 순번을 붙인다 (`${i}-${text}`). 같은 문구가 두 번 나올 수 있다.
- **새 화면 = 라우트 + 기능 폴더 + 메뉴 한 줄** (`/add-page`). 모든 화면은 `AppShell`(사이드바 + 상단 헤더 `h-12`) 안에 그려진다.
  - 화면 전체 높이를 쓰는 페이지(채팅 등)는 루트를 `h-[calc(100svh-3rem)]`로, 스크롤은 페이지가 아니라 내부 목록(`min-h-0 flex-1 overflow-y-auto`)에서.
  - 같은 이름의 라우트·기능 폴더를 두 사람이 만들지 않게, 시작 전에 `ls frontend/src/app frontend/src/features`와 열린 PR을 확인한다 (`/pr-check`가 PR 전에 다시 잡는다).
