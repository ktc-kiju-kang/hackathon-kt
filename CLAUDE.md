# KT 해커톤 프로젝트

> 3명이 동시에 Claude Code로 작업하는 레포. **이 파일은 팀 공용 규칙**이며, 개인 메모는 `CLAUDE.local.md`(gitignore됨)에 쓴다.

## 프로젝트 개요
- 주제: _TBD_
- 저장소: https://github.com/kiju-kang/hackathon-kt (공개 — 비밀값 절대 커밋 금지)
- 웹: `web/` — Vite + React + TypeScript
  - 실행: `cd web && npm install && npm run dev` (http://localhost:5173)
  - 검증: `cd web && npm run lint && npm run build` (CI가 PR마다 동일하게 실행)
  - API 호출은 `web/src/api/client.ts`에 모은다. `VITE_API_BASE_URL`이 비면 mock으로 동작
  - 배포: main 머지 시 GitHub Pages 자동 배포 → https://kiju-kang.github.io/hackathon-kt/
- 백엔드/기타: _TBD_ (확정되면 여기 + `docs/decisions/`에 기록)

## 팀 & 소유 영역
상세는 `docs/TEAM.md`. 작업 전 **자기 소유 영역 밖 파일을 수정해야 하면 먼저 팀에 알린다.**

## 동시 작업 규칙 (Claude도 반드시 따를 것)
1. **main에 직접 커밋 금지.** 브랜치명: `<member>/<task-id>-<짧은설명>` (예: `a/T-003-login-api`)
2. **동시에 여러 작업을 할 땐 git worktree 사용:** `scripts/new-worktree.sh <member> <task-id> <설명>`
3. **공유 인터페이스(API 스펙, 타입, DB 스키마)는 `docs/CONTRACTS.md`가 단일 진실.** 계약 변경은 별도 작은 PR로 먼저 머지 후 구현.
4. **충돌 방지:** 공용 파일(BOARD 류)을 함께 편집하지 않는다.
   - 진행상황 → `docs/status/<member>.md` (본인 파일만 수정)
   - 작업 → `tasks/T-xxx-*.md` (작업당 1파일, owner만 수정)
5. **작게, 자주 머지.** 작업 시작 전과 PR 전 `scripts/sync.sh`로 main 반영.
6. 커밋 메시지: `<type>(<scope>): <요약>` — type: feat/fix/refactor/docs/chore/test
7. 비밀값은 `.env`에만. `.env.example`에 키 이름만 추가.

## Claude 작업 방식
- 세션 시작 시 훅이 브랜치/동기화 상태와 팀원 현황을 보여준다. main보다 뒤처져 있으면 먼저 sync를 제안할 것.
- 작업 시작: `/start-task`, 동기화: `/sync`, 작업 마무리/인계: `/handoff`, 팀 현황: `/team-status`
- PR 전에는 `reviewer` 서브에이전트로 셀프 리뷰.
- 다른 사람 소유 영역이나 `docs/CONTRACTS.md`를 바꿔야 하면 **직접 수정하지 말고 사용자에게 먼저 확인.**
