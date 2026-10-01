# 팀

| 이름 | GitHub |
|---|---|
| 김정남 | `ktc-bill-kim` |
| 김재혁 | `ktc-jehyuk-kim` |
| 강기주 | `ktc-kiju-kang` |

연락처는 공개 레포이므로 여기 적지 않는다.

## 담당 방식
- 고정 역할·디렉터리 담당 없음. **기능(이슈) 단위**로 assignee가 frontend + backend + DB를 끝까지 맡는다.
- 누가 무엇을 하는지는 칸반(GitHub Projects)이 단일 진실. 이 문서에 따로 적지 않는다.
- 공용 영역(`CLAUDE.md`, `.claude/`, `.github/`, `render.yaml`, `frontend/src/app/layout.tsx`, `frontend/src/lib/api-client.ts`, `backend/app/main.py`, `backend/app/config.py`, `backend/app/db.py`, `database/`)은 변경 시 다른 1명 이상 리뷰.

## 칸반 (GitHub Projects)
- 보드: https://github.com/users/ktc-kiju-kang/projects/1 (팀원 모두 Write 권한)
- 컬럼: Todo → In Progress → In Review → Done
- 카드 = 이슈 (템플릿: 기능 / 버그). 작업 시작 시 본인 assign + In Progress
- PR에 `Closes #번호` → 머지 시 이슈 닫힘 → Done
- Project 자동화(Workflows, 보드 ⋯ → Workflows): Auto-add to project(repo 이슈) → Todo, Item closed → Done, Pull request merged → Done

## 권한
- main 보호: PR + CI(`frontend`, `backend`) + 1명 승인. 관리자(owner `ktc-kiju-kang`)만 우회 가능
- 이전 저장소 `kiju-kang/hackathon-kt`(PR #1~#5 기록)는 더 이상 사용하지 않는다
- 저장소 설정은 관리자만 변경. Vercel·Render·Supabase 대시보드 접근 권한은 _TBD_

## 커뮤니케이션
- 채널: _TBD_
- 싱크 타임: _TBD_ (예: 3시간마다 10분)
