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
- 공용 영역(`CLAUDE.md`, `.claude/`, `.github/`, `render.yaml`, `scripts/`, `frontend/src/app/layout.tsx`, `frontend/src/components/app-shell.tsx`·`app-sidebar.tsx`, `frontend/src/lib/api-client.ts`, `backend/app/main.py`·`backend/app/core/`, `backend/app/agent/`(도구 파일 제외), `database/`)은 변경 시 리뷰를 요청하고 답을 받은 뒤 머지한다 (승인은 필수 아님). 사이드바 메뉴 한 줄 추가는 예외적으로 가볍게 봐도 된다.

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
- 팀 운영 규칙: main에는 직접 commit·push하지 않고 PR + CI(`frontend`, `backend`)로 반영한다. **승인은 필수가 아니며 머지는 사람이 한다.** 공용 파일·남의 기능·계약·마이그레이션 변경은 리뷰를 요청하고 답을 받은 뒤 머지한다. 작업 시작 전·PR 전에 main을 반영하고 `/pr-check`를 실행한다.
- **설정 확인 이력**: 2026-10-03 기록상 위 2개 필수 체크·승인 불필요·관리자 우회 가능, 최신 main 강제 옵션은 없었다. 2026-10-06에는 `main.protected=true`만 확인됐고 세부 보호 설정은 API 404로 재확인하지 못했다. **저장소 설정의 강제와 팀 운영 규칙을 구분**한다. 상세는 [SDLC](SDLC.md#2-완료의-정의-definition-of-done).
- 이전 저장소 `kiju-kang/hackathon-kt`(기록: kiju-kang/hackathon-kt#1~kiju-kang/hackathon-kt#5)는 더 이상 사용하지 않는다.
- 저장소 설정은 관리자만 변경한다. Vercel·Render·Supabase의 실제 접근 가능자와 대체 담당자는 아직 문서로 확인되지 않았다. 시연 전 접근 가능 여부를 확인하고 **GitHub ID·확인 일자만** 남긴다. 키·계정 공유나 비밀번호 기록으로 대신하지 않는다.

## 커뮤니케이션
- **결정·인수 기록**: 관련 GitHub 이슈·PR 댓글에 남긴다. 실시간 대화에서 정한 범위·계약·장애 조치도 해당 이슈로 옮겨 추적 가능하게 한다.
- 실시간 채널·정기 싱크 시간은 아직 미정이다. 확정 전에는 해당 이슈/PR에서 담당자를 멘션하고, 답변이 필요한 공용·계약 변경은 기다린다. 응답 시간 보장은 정해져 있지 않다.
- 이슈 생성·push·PR 생성·수동 재배포는 사용자 확인 후 진행한다. 공유 DB에 직접 SQL을 실행하지 않는다.

## 역할별 인수 책임

고정 기능 담당을 새로 지정하지 않는다. 실제 담당자는 이슈 assignee를 따르며, 빈 역할을 AI가 임의로 특정 팀원에게 배정하지 않는다.

| 역할 | 맡는 일 | 남길 증거 |
|---|---|---|
| 기능 이슈 담당 | 범위·계약·구현·검증·배포 후 기능 인수 | 완료 조건별 결과, PR·CI·Deploy 링크, 미해결 항목 |
| 영향받는 기능/공용 변경 리뷰어 | 계약·다른 기능 영향·DB 호환성 검토 | 리뷰 답변과 지적 처리 결과 |
| PR 머지 수행자 | CI·리뷰 상태 확인 후 머지, 배포 확인 담당 지정 | 머지 SHA와 인계 댓글 |
| 저장소·서비스 권한 보유자 | 보호 설정·환경변수·배포 로그·복구 지원 | 확인 일자·대상·결과, 비밀값 없는 조치 기록 |
| 시연 담당 | 최종 리허설·예비안·변경 동결 관리 | #32의 [리허설 결과](DEMO.md#리허설-기록-32에-댓글로-남긴다) |

칸반의 Done 자동 이동은 머지/이슈 종료 상태일 뿐 운영 인수 판정이 아니다. 배포·리허설이 실패하면 이슈를 다시 열거나 연결된 후속 이슈로 담당과 재확인 조건을 남긴다.
