---
name: issue-monitor
description: GitHub Issue 진행 상태를 30초마다 확인해 Slack 으로 알리고 로컬 HTML 대시보드(http://127.0.0.1:8765)로 보여준다. "이슈 모니터 켜줘/꺼줘/상태", "대시보드 띄워줘", "슬랙 알림" 요청에 사용.
---

Issue(티켓)의 진행 상태(대기 → 선점 → PR → 체크 → 머지 → main CI → 완료)를 지켜보는 도구다.
본체는 `scripts/issue-monitor.py`(표준 라이브러리 + `gh`, **LLM 토큰을 쓰지 않는다**), 켜고 끄는 건 `scripts/monitor.sh`.
`/ticket-loop`(Issue를 구현하는 쪽)와 별개다 — 이쪽은 **보기만** 하고 아무것도 바꾸지 않는다.

## 쓰는 법
| 하려는 일 | 명령 |
|---|---|
| 켜기 (백그라운드, 대시보드를 브라우저로 연다) | `scripts/monitor.sh start` 또는 `make monitor` |
| 상태 확인 (켜졌는지, 마지막 확인 시각, 연속 실패) | `scripts/monitor.sh status` |
| 대시보드만 다시 열기 | `scripts/monitor.sh open` → http://127.0.0.1:8765 |
| 끄기 | `scripts/monitor.sh stop` 또는 `make monitor-stop` |
| 로그 | `scripts/monitor.sh logs` |
| Slack 없이 대시보드만 | `scripts/monitor.sh start --no-slack` |
| Slack 으로 안 보내고 화면에 찍어 시험 | `python3 scripts/issue-monitor.py --once --dry-run` |

옵션은 `start` 뒤에 그대로 이어 쓴다 (`--interval 60`, `--quiet-start`, `--port` 대신 `MONITOR_PORT=9000`). 브라우저를 열지 않으려면 `MONITOR_NO_OPEN=1`.
사용자가 켜 달라고 하면 `start` 후 **출력된 주소**와 `status` 결과를 알려 준다. 이미 켜져 있으면 `start`는 안내만 한다.

## 무엇을 알리나 (Slack 한 주기에 한 메시지로 묶는다)
🆕 새 이슈(외부 작성자는 ⚠️ 표시) · 🔒 선점/🔓 해제(`claim/<번호>`) · 🙋 `needs-info`/`needs-human`/`blocked` · ⏸️ `agent-pause` ·
💬 새 댓글(작성자·앞부분) · 🔀 PR 열림 · 🟢 체크 통과/🔴 실패(실패한 체크 이름) · 🎉 머지 · 🚀/🚨 main CI 통과/실패 · ✅ 닫힘/♻️ 다시 열림.
처음 켜면 현재 상태를 기준선으로만 저장하고 시작 알림 한 건만 보낸다 (알림 폭탄 없음).

## 외부 저장소 감시
다른 저장소도 같이 본다: `~/.config/hackathon-kt/monitor-watch`에 한 줄에 `OWNER/NAME` 하나(# 주석 가능), 또는 `scripts/monitor.sh start --watch OWNER/NAME`.
**감시 모드**는 호출을 아끼려고 새 이슈·PR 열림·머지·닫힘, 이슈 닫힘만 알린다 (댓글·체크·선점·main CI 제외). Slack 문구 앞에 `[저장소명]`이 붙고 대시보드 제목의 선택 상자로 저장소를 바꾼다. 처음엔 조용히 기준선만 잡는다.

## 팀원 캐릭터 (선택, 로컬 설정)
대시보드의 일꾼·수령인을 실제 팀원 모습으로 바꾸려면 `~/.config/hackathon-kt/monitor-avatars.json`에 GitHub 계정별로 적는다 (재시작 없이 다음 주기에 반영).
키: `name`(화면에 쓸 이름), `style`(0~6 헤어), `hair`·`skin`(`["#주색","#그늘색"]`), `top`·`pants`·`jacket`(`#rrggbb`), `glasses`(`round`|`thick`), `stubble`(true).
**이름·외모는 개인정보라 저장소에 커밋하지 않는다** (공개 저장소). 설정이 없으면 티켓마다 무작위 캐릭터가 나온다. 값은 서버가 검증해서(색은 `#rrggbb`만, 이름 20자) 대시보드로 보낸다.

## 대시보드
칸반 5열: 📥 대기 · 🙋 사람 확인 · 🔒 진행 중 · 🔀 리뷰·머지 대기(체크 상태) · ✅ 완료(main CI 결과) + 오른쪽에 최근 알림 타임라인.
5초마다 새로 고침, 상단에 마지막 확인 시각·GitHub 조회 실패 횟수·Slack 상태. 읽기 전용이고 `127.0.0.1`에서만 열린다 (Host 헤더 검증).

## Slack webhook — 시크릿
- 위치: 환경변수 `SLACK_WEBHOOK_URL`, 없으면 파일 `~/.config/hackathon-kt/slack-webhook`(권한 600, `https://hooks.slack.com/services/…` 형식만 허용).
- **저장소·문서·커밋·PR·로그·대화에 URL을 쓰지 않는다.** 출력할 일이 있어도 가리고, 실패 로그에도 URL이 나오지 않는다 (코드가 막는다).
- URL이 노출됐다고 의심되면 Slack 앱 설정에서 webhook 을 새로 만들고 위 파일을 교체한다.

## 문제 해결
- `Slack webhook 이 없다` → 위 파일/환경변수를 만들거나 `--no-slack`.
- 대시보드가 안 열림 → `scripts/monitor.sh status`, 포트 사용 중이면 `MONITOR_PORT=9000 scripts/monitor.sh start`.
- `GitHub 조회 N회 연속 실패` → `gh auth status` (회사 EMU 계정 로그인), 5회 연속이면 Slack 으로도 경고가 가고 복구되면 알려 준다. rate limit 이면 자동으로 간격을 늘린다.
- 알림이 갑자기 한꺼번에 쏟아진다 → 상태 파일(`~/.cache/hackathon-kt/issue-monitor-<저장소>.json`)이 지워진 경우다. 처음부터 다시 기준선을 잡으니 한 번만 그렇다.
- Slack 전송이 실패하면 상태를 갱신하지 않아 다음 주기(30초 뒤)에 같은 알림을 다시 보낸다.
