---
name: deploy-status
description: 배포 상태 확인 — GitHub Pages(web)와 Render(api)가 최신 main으로 정상 동작하는지 점검. 배포 확인, 데모 직전 점검 시 사용.
---
1. `gh run list --branch main --limit 5`로 CI·Pages 배포 워크플로 결과를 확인한다.
2. API: `curl -s -m 90 https://hackathon-kt-api.onrender.com/api/health` (free 플랜은 잠들어 있으면 첫 응답이 ~1분). 200과 `"status":"ok"` 확인.
3. CORS: `curl -s -i -H "Origin: https://kiju-kang.github.io" https://hackathon-kt-api.onrender.com/api/health | grep -i access-control-allow-origin`
4. Web: `https://kiju-kang.github.io/hackathon-kt/` HTML이 200인지, 번들 JS에 `hackathon-kt-api.onrender.com`이 포함됐는지 확인 (`VITE_API_BASE_URL` 주입 여부).
5. 결과를 항목별 정상/이상으로 요약한다. Render 배포 자체 실패는 대시보드 로그를 확인하라고 안내한다 (CLI 접근 없음).
