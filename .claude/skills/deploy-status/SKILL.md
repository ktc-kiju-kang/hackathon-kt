---
name: deploy-status
description: 배포 상태 확인 — Vercel(frontend), Render(backend), CORS가 최신 main으로 정상 동작하는지 점검. 배포 확인, 데모 직전 점검 시 사용.
---
1. `gh run list --branch main --limit 5`로 CI 결과를 확인한다.
2. Vercel: 최신 main 커밋의 배포 상태를 `gh api repos/kiju-kang/hackathon-kt/commits/main/status --jq '.statuses[] | {context, state, target_url}'`로 확인한다 (Vercel이 커밋 상태를 남긴다). 프로덕션 URL은 CLAUDE.md 개요 참고, HTML 200 확인. 화면의 API 상태가 `mock`이면 Vercel 환경변수 `NEXT_PUBLIC_API_BASE_URL` 누락이다.
3. API: `curl -s -m 90 https://hackathon-kt-api.onrender.com/api/health` (free 플랜은 잠들어 있으면 첫 응답 ~1분). 200과 `"status":"ok"` 확인.
4. CORS: `curl -s -i -H "Origin: <Vercel 프로덕션 URL>" https://hackathon-kt-api.onrender.com/api/health | grep -i access-control-allow-origin`
5. 결과를 항목별 정상/이상으로 요약한다. Vercel·Render 빌드 실패는 각 대시보드 로그를 확인하라고 안내한다 (CLI 접근 없음).
