---
name: new-issue
description: 칸반 카드(GitHub 이슈) 생성 — 기능/버그 템플릿에 맞춰 목표·완료 조건·API 초안을 채워 이슈를 만든다. 새 기능이나 할 일을 칸반에 올리거나 기능을 이슈로 쪼갤 때 사용.
argument-hint: <기능 설명>
---
이슈를 만든다: $ARGUMENTS

1. 설명을 바탕으로 `.github/ISSUE_TEMPLATE/feature.yml`(또는 bug.yml) 형식의 본문을 작성한다:
   - 제목: `[<feature>] <사용자 관점 요약>` (feature는 kebab-case, 폴더명으로 쓰임)
   - 목표 / 완료 조건(체크리스트) / API·계약 초안 / 의존 이슈
2. 기능이 크면(하루 이상, frontend+backend 각각 큼) 독립적으로 머지 가능한 이슈 여러 개로 쪼개자고 제안한다. 각 이슈는 한 사람이 frontend+backend 끝까지 할 수 있는 크기.
3. 기존 이슈와 중복·의존 관계를 `gh issue list --state open`으로 확인한다.
4. 초안을 사용자에게 보여주고 확인받은 뒤 생성한다:
   `gh issue create --title "..." --body "..." --label feature` (담당자가 정해졌으면 `--assignee <id>`)
   - 칸반 보드에는 Auto-add 자동화로 Todo에 자동 등록된다 (`--project` 불필요).
5. 생성된 이슈 번호와 URL을 알려주고, 바로 시작하려면 `/start-task <번호>`를 안내한다.
