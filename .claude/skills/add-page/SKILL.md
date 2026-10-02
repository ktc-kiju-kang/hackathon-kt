---
name: add-page
description: 새 화면(페이지) 추가 — Next.js 라우트, 기능 폴더 컴포넌트, 사이드바 메뉴 한 줄, AppShell 레이아웃 규칙. 새 화면·메뉴·페이지를 만들 때 사용.
argument-hint: <경로> <메뉴 이름> <설명>
---
새 화면을 추가한다: $ARGUMENTS

1. **이름 충돌 확인 (먼저)** — 같은 화면을 두 사람이 만들지 않게:
   - `ls frontend/src/app frontend/src/features`로 기존 라우트·기능 폴더 확인
   - `gh pr list --state open`과 각 PR의 `frontend/src/app/` 변경(`gh pr diff <n> --name-only`)에 같은 경로가 있는지 확인
   - 겹치면 멈추고 사용자에게 묻는다 (다른 경로 / 기존 화면에 합치기 / 담당자와 상의)
2. **라우트** — `frontend/src/app/<경로>/page.tsx`: 서버 컴포넌트로 두고 기능 컴포넌트만 렌더. 제목은 `export const metadata = { title: '<이름> · KT 해커톤' }`.
3. **기능 폴더** — `frontend/src/features/<feature>/`: 화면 컴포넌트(`'use client'`는 필요한 것만), API가 있으면 `api.ts`(`@/lib/api-client`, mock 포함 — `/add-endpoint`).
   - 다른 기능 폴더에 파일을 넣지 않는다 (예: 채팅 비슷한 화면이라도 AI 에이전트 대화 기능인 `features/chat`에 넣지 말고 새 폴더).
4. **레이아웃 규칙** (AppShell 안에 그려짐: 좌측 사이드바 + 상단 헤더 `h-12`)
   - 일반 페이지: `mx-auto w-full max-w-<n> px-4 py-6`
   - 화면 높이를 꽉 쓰는 페이지: 루트 `h-[calc(100svh-3rem)] flex flex-col`, 스크롤은 내부 목록(`min-h-0 flex-1 overflow-y-auto`)
   - shadcn 컴포넌트·테마 토큰만 사용 (CLAUDE.md frontend 규칙)
   - 차트: `npx shadcn@latest add chart`(recharts)가 이미 있다. 계열 색·범례·키 규칙은 CLAUDE.md frontend "차트 계열 색", 예시는 `features/trends/TrendCharts.tsx`
   - 다른 화면으로 값을 넘길 때는 그 기능의 `api.ts`에 저장·읽기 함수를 두고 계약에 적는다 (예: radar → product, `sessionStorage`)
5. **메뉴** — `frontend/src/components/app-sidebar.tsx`의 `MENU_GROUPS`에 `{ title, href, icon }` 한 줄 (lucide 아이콘). 공용 파일이므로 **이 한 줄 외에는 고치지 않는다.** 새 그룹이 필요하면 사용자에게 확인.
6. **검증** — `cd frontend && npm run lint && npm run build` (빌드 출력에 새 라우트가 보이는지), 가능하면 `npm run dev`로 화면 확인 (개발 서버는 첫 로드가 느려 클릭이 무시될 수 있다 — 잠시 기다린 뒤 확인).
7. README의 "화면" 표에 한 줄 추가.
