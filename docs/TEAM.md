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
- 공용 영역(`CLAUDE.md`, `.claude/`, `.github/`, `render.yaml`, `scripts/`, `frontend/src/app/layout.tsx`, `frontend/src/components/app-shell.tsx`·`app-sidebar.tsx`, `frontend/src/lib/api-client.ts`, `backend/app/main.py`·`config.py`·`db.py`, `backend/app/agent/`(도구 파일 제외), `database/`)은 변경 시 다른 1명 이상 리뷰. 사이드바 메뉴 한 줄 추가는 예외적으로 가볍게 봐도 된다.

## 칸반 (GitHub Projects)
- 보드: https://github.com/users/ktc-kiju-kang/projects/1 (팀원 모두 Write 권한)
- 컬럼: Todo → In Progress → In Review → Done
- 카드 = 이슈 (템플릿: 기능 / 버그)

| 상태 | 언제 | 누가 옮기나 |
|---|---|---|
| Todo | 이슈 생성 | 자동 (Auto-add `is:issue is:open` + Item added) |
| In Progress | 작업 시작 | **사람** — `/start-task`가 assign과 함께 옮김, 또는 카드 드래그 |
| In Review | PR에 `Closes #번호` 연결 | 자동 (Pull request linked to issue) |
| Done | PR 머지 / 이슈 닫힘 | 자동 (Pull request merged, Item closed) |

- 카드를 Done으로 끌면 이슈도 닫힌다 (Auto-close issue). 실수로 끌었으면 이슈를 Reopen.
- 자동화 설정: 보드 ⋯ → Workflows (Status 옵션을 바꾸면 각 워크플로의 값이 풀리므로 다시 지정)

## 권한
- main 보호: PR + CI(`frontend`, `backend`) + 1명 승인. **승인 후 새 push 시 승인 자동 취소**. 최신 main 반영은 필수 아님(대신 `/pr-check`). 관리자(owner `ktc-kiju-kang`)만 우회 가능
- 이전 저장소 `kiju-kang/hackathon-kt`(PR #1~#5 기록)는 더 이상 사용하지 않는다
- 저장소 설정은 관리자만 변경. Vercel·Render·Supabase 대시보드 접근 권한은 _TBD_

## 커뮤니케이션
- 채널: _TBD_
- 싱크 타임: _TBD_ (예: 3시간마다 10분)
