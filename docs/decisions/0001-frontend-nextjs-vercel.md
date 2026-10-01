# 0001. 프론트엔드: Next.js + shadcn/ui, Vercel 배포

- 상태: 채택 (초기 Vite + GitHub Pages 구성을 대체)
- 날짜: 2026-10-01

## 결정
`frontend/`에 Next.js(App Router, TS) + Tailwind v4 + shadcn/ui(radix-nova). 배포는 Vercel (Root Directory: `frontend`).

## 이유
- 파일 기반 라우팅(`src/app/<route>/page.tsx`)으로 3명이 화면 단위로 병렬 작업할 때 충돌이 적다.
- Vercel은 PR마다 프리뷰 URL을 제공해 리뷰가 쉽다. SSR·API Routes 제약이 없다.

## 트레이드오프
- 데이터·비즈니스 로직은 FastAPI에 둔다. Next.js Route Handler/Server Action에 백엔드 로직을 넣지 않는다 (계약이 두 곳으로 흩어짐).
- `NEXT_PUBLIC_*`는 빌드 시점에 번들에 고정된다. 값 변경 시 재배포 필요.
