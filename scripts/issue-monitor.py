#!/usr/bin/env python3
"""GitHub Issue 진행 상태 모니터 → Slack + 로컬 HTML 대시보드.

표준 라이브러리와 `gh` CLI 만 쓴다 (LLM 토큰을 쓰지 않는다).

  scripts/issue-monitor.py            30초마다 확인, 상태가 바뀌면 Slack 으로 (Ctrl-C 로 종료)
  scripts/issue-monitor.py --once     한 번만 확인
  scripts/issue-monitor.py --dry-run  Slack 으로 보내지 않고 화면에 출력 (webhook 없이 시험)
  scripts/issue-monitor.py --serve    + 대시보드 http://127.0.0.1:8765 (읽기 전용, 이 PC 에서만)
  옵션: --interval 30  --repo OWNER/NAME  --quiet-start (시작 알림 생략)  --state-file 경로
        --port 8765  --no-slack (Slack 없이 대시보드만)  --open (브라우저 열기)
  백그라운드 실행·중지·상태: scripts/monitor.sh start|stop|status|logs (또는 /issue-monitor 스킬)

알리는 상태: 새 이슈 · 선점/해제(scripts/claim.sh 의 claim/<번호> ref) ·
  needs-info/needs-human/blocked 라벨 · 새 댓글 · PR 열림 · 체크 통과/실패 · 머지 ·
  main CI 결과 · 이슈 닫힘/다시 열림.

Slack webhook 은 시크릿이다 (저장소·로그에 넣지 않는다):
  환경변수 SLACK_WEBHOOK_URL, 없으면 ~/.config/hackathon-kt/slack-webhook (권한 600).
처음 실행하면 현재 상태를 기준선으로만 저장하고(알림 폭탄 방지) 시작 알림 한 건만 보낸다.
상태 파일: ~/.cache/hackathon-kt/issue-monitor-<저장소>.json (ISSUE_MONITOR_STATE 로 변경).
Slack 전송이 실패하면 그 항목의 상태를 갱신하지 않아 다음 주기에 다시 보낸다.
GitHub 조회가 5번 연속 실패하면 경고하고, 복구되면 알린다.
공개 저장소라 제목·댓글은 신뢰할 수 없는 입력이다: Slack 멘션(<!channel> 등)과 링크가
되지 않게 이스케이프하고 길이를 자른다.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

TRUSTED = ("OWNER", "MEMBER", "COLLABORATOR")
BLOCK_LABELS = ("needs-info", "needs-human", "blocked", "agent-pause")
FAIL_STATES = ("FAILURE", "TIMED_OUT", "STARTUP_FAILURE", "ACTION_REQUIRED", "ERROR")
WEBHOOK_RE = re.compile(r"^https://hooks\.slack\.com/services/[A-Za-z0-9/_-]+$")
BRANCH_RE = re.compile(r"^[a-z]+/(\d+)-")
CLOSES_RE = re.compile(r"(?i)\b(?:closes|fixes|resolves)\s+#(\d+)\b")
MAX_FAILS_BEFORE_ALERT = 5


# ---------- 순수 함수 (테스트 대상) ----------


def esc(text, limit: int = 120) -> str:
    """Slack mrkdwn 에 안전하게: & < > 이스케이프(멘션·링크 무력화), 한 줄로, 길이 제한."""
    t = " ".join(str(text or "").split())
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    t = t.replace("`", "'").replace("*", "∗").replace("~", "∼")
    return t if len(t) <= limit else t[:limit] + "…"


MRKDWN_LINK_RE = re.compile(r"<(https://github\.com/[^|>]+)\|([^>]*)>")


def plain(text: str) -> str:
    """Slack mrkdwn → 대시보드용 평문 (링크는 라벨만, 이스케이프 해제).

    화면에는 textContent 로만 넣는다.
    """
    t = MRKDWN_LINK_RE.sub(lambda m: m.group(2), text)
    t = re.sub(r"\*([^*\n]+)\*", r"\1", t)  # 우리가 붙인 Slack 굵게 표시 제거
    return html.unescape(t).replace("`", "").replace("∗", "*")


def first_url(text: str) -> str:
    m = MRKDWN_LINK_RE.search(text)
    return m.group(1) if m else ""


def link(url: str, label: str) -> str:
    """GitHub URL 만 링크로 만든다 (그 밖의 URL 은 글자로만)."""
    if url.startswith("https://github.com/"):
        return f"<{url}|{esc(label, 100)}>"
    return esc(label, 100)


def summarize_checks(rollup) -> tuple:
    """statusCheckRollup → ('none'|'pending'|'success'|'failure', 실패한 체크 이름들).
    CANCELLED·SKIPPED·NEUTRAL 은 무시한다 (새 push 로 대체된 실행이 흔하다)."""
    pending, failing, seen = False, [], False
    for c in rollup or []:
        status = (c.get("status") or "").upper()
        concl = (c.get("conclusion") or c.get("state") or "").upper()
        name = c.get("name") or c.get("context") or "?"
        if "state" in c and "status" not in c:  # StatusContext (예: Vercel)
            if concl == "PENDING":
                pending, seen = True, True
            elif concl in FAIL_STATES:
                failing.append(name)
                seen = True
            elif concl == "SUCCESS":
                seen = True
            continue
        if status and status != "COMPLETED":
            pending, seen = True, True
        elif concl in FAIL_STATES:
            failing.append(name)
            seen = True
        elif concl == "SUCCESS":
            seen = True
    if pending:
        return "pending", failing
    if failing:
        return "failure", sorted(set(failing))
    return ("success" if seen else "none"), []


def linked_issues(pr: dict) -> list:
    nums = set()
    m = BRANCH_RE.match(pr.get("headRefName") or "")
    if m:
        nums.add(int(m.group(1)))
    nums.update(int(x) for x in CLOSES_RE.findall(pr.get("body") or ""))
    return sorted(nums)


def issue_entity(issue: dict, claim_owner) -> dict:
    labels = sorted(n for n in issue["labels"] if n in BLOCK_LABELS)
    return {
        "title": issue["title"],
        "url": issue["url"],
        "state": issue["state"],  # open | closed
        "reason": issue.get("reason") or "",
        "labels": labels,
        "claim": claim_owner or "",
        "assignees": sorted(issue["assignees"]),
        "comments": issue["comments"],
        "assoc": issue["assoc"],
        "author": issue["author"],
        "closed_by": issue.get("closed_by") or "",
    }


def pr_entity(pr: dict, main_ci: str) -> dict:
    checks, failing = summarize_checks(pr.get("statusCheckRollup"))
    state = "merged" if pr.get("mergedAt") else pr["state"].lower()
    return {
        "title": pr["title"],
        "url": pr["url"],
        "state": state,  # open | merged | closed
        "checks": checks,
        "failing": failing,
        "issues": linked_issues(pr),
        "merge_sha": ((pr.get("mergeCommit") or {}).get("oid") or "")[:7],
        "author": (pr.get("author") or {}).get("login") or "",
        "merged_by": (pr.get("mergedBy") or {}).get("login") or "",
        "main_ci": main_ci,
    }


def diff_issue(n: int, old, new: dict, fetch_comments) -> list:
    """이슈 상태 변화 → 알림 문장 목록. old 가 None 이면 새로 생긴 이슈."""
    ref = f"{link(new['url'], esc(new['title'], 80))} *#{n}*"
    ev = []
    if old is None:
        if new["state"] == "open":
            who = new["author"] + ("" if new["assoc"] in TRUSTED else " ⚠️ 외부 작성자")
            ev.append(f"🆕 새 이슈 · {esc(who, 60)}")
        return [f"{ref} — {e}" for e in ev]
    if old["state"] != new["state"]:
        if new["state"] == "closed":
            who = f" · {esc(new['closed_by'], 40)}" if new.get("closed_by") else ""
            ev.append(
                ("🚫 닫힘 (계획 없음)" if new["reason"] == "not_planned" else "✅ 닫힘 (완료)")
                + who
            )
        else:
            ev.append("♻️ 다시 열림")
    if new["state"] == "open":
        if not old["claim"] and new["claim"]:
            ev.append("🔒 선점 · {}".format(esc(new["claim"], 40)))
        elif old["claim"] and not new["claim"]:
            ev.append("🔓 선점 해제")
        elif not new["claim"] and set(new["assignees"]) - set(old["assignees"]):
            ev.append("👤 담당 지정 · {}".format(esc(", ".join(new["assignees"]), 60)))
        for lb in sorted(set(new["labels"]) - set(old["labels"])):
            ev.append(
                f"🙋 `{esc(lb, 30)}` — 사람 확인 필요"
                if lb != "agent-pause"
                else "⏸️ `agent-pause` — 루프 일시 정지"
            )
        for lb in sorted(set(old["labels"]) - set(new["labels"])):
            ev.append(f"▶️ `{esc(lb, 30)}` 해제")
    if new["comments"] > old["comments"]:
        added = new["comments"] - old["comments"]
        last = fetch_comments(n, added) or []
        if last:
            for c in last[-3:]:
                tag = "" if c["assoc"] in TRUSTED else " ⚠️외부"
                ev.append("💬 {}{}: {}".format(esc(c["user"], 40), tag, esc(c["body"], 100)))
        else:
            ev.append(f"💬 새 댓글 {added}개")
    return [f"{ref} — {e}" for e in ev]


def merged_by_text(pr: dict) -> str:
    """머지한 사람과 작성자. 같은 사람이면 한 번만 보여 준다."""
    by, author = pr.get("merged_by") or "", pr.get("author") or ""
    if by and author and by != author:
        return f" · 머지 {esc(by, 40)} (작성 {esc(author, 40)})"
    return f" · {esc(by or author, 40)}" if (by or author) else ""


def diff_pr(n: int, old, new: dict) -> list:
    ref = f"{link(new['url'], esc(new['title'], 80))} *PR #{n}*"
    for_issue = (
        (" (이슈 " + ", ".join(f"#{i}" for i in new["issues"]) + ")") if new["issues"] else ""
    )
    opened_by = f" · {esc(new['author'], 40)}" if new.get("author") else ""
    merged = merged_by_text(new)
    ev = []
    if old is None:
        if new["state"] == "open":
            ev.append(f"🔀 PR 열림{opened_by}{for_issue}")
        elif new["state"] == "merged":
            ev.append(f"🎉 머지됨{merged}{for_issue}")
    else:
        if old["state"] == "open" and new["state"] == "merged":
            ev.append(f"🎉 머지됨{merged}{for_issue}")
        elif old["state"] == "open" and new["state"] == "closed":
            ev.append(f"⛔ PR 닫힘 (머지 안 됨){for_issue}")
        elif old["state"] != new["state"] and new["state"] == "open":
            ev.append(f"♻️ PR 다시 열림{for_issue}")
        if new["state"] == "open" and old["checks"] != new["checks"]:
            if new["checks"] == "success":
                ev.append("🟢 체크 통과")
            elif new["checks"] == "failure":
                ev.append("🔴 체크 실패 · {}".format(esc(", ".join(new["failing"]), 100)))
        if new["state"] == "merged" and old["main_ci"] != new["main_ci"]:
            sha = new["merge_sha"]
            if new["main_ci"] == "success":
                ev.append(f"🚀 main CI 통과 ({esc(sha, 10)})")
            elif new["main_ci"] == "failure":
                ev.append(f"🚨 main CI 실패 ({esc(sha, 10)})")
    return [f"{ref} — {e}" for e in ev]


def run_cycle(
    state: dict, snapshot: dict, send, fetch_comments, quiet_start: bool = False
) -> dict:
    """한 주기. state: {'issues':{}, 'prs':{}}, snapshot: 같은 모양의 새 상태.

    첫 실행(state 가 비었음)이면 기준선만 저장하고 시작 알림 한 건만 보낸다.
    전송이 실패하면 그 항목은 옛 상태를 유지해 다음 주기에 다시 보낸다.
    """
    if not state.get("init"):
        if not quiet_start:
            n_i = sum(1 for e in snapshot["issues"].values() if e["state"] == "open")
            n_p = sum(1 for e in snapshot["prs"].values() if e["state"] == "open")
            send(
                [
                    f"👀 이슈 모니터 시작 — 열린 이슈 {n_i}개, 열린 PR {n_p}개 "
                    "(이후 변화만 알립니다)"
                ]
            )
        return {"init": True, "issues": snapshot["issues"], "prs": snapshot["prs"]}

    new_state = {"init": True, "issues": dict(state["issues"]), "prs": dict(state["prs"])}
    lines, touched = [], []
    for key in ("issues", "prs"):
        for num, ent in snapshot[key].items():
            old = state[key].get(num)
            if old == ent:
                continue
            n = int(num)
            ev = (
                diff_issue(n, old, ent, fetch_comments)
                if key == "issues"
                else diff_pr(n, old, ent)
            )
            if ev:
                lines += ev
                touched.append((key, num, ent))
            else:
                new_state[key][num] = ent  # 알릴 일 없는 변화는 조용히 갱신
    if lines and not send(lines):
        return new_state  # 전송 실패: 알릴 항목은 옛 상태 그대로 → 다음 주기에 재시도
    for key, num, ent in touched:
        new_state[key][num] = ent
    return new_state


# ---------- 대시보드 (로컬 HTML, 읽기 전용) ----------

HTML_PATH = Path(__file__).with_name("issue-monitor.html")
EVENT_LIMIT = 100


def _now_iso() -> str:
    # datetime.UTC 는 3.11+ 이라 쓰지 않는다 (시스템 python3 가 3.9 일 수 있다)
    return datetime.now(timezone.utc).isoformat(timespec="seconds")  # noqa: UP017


class Dash:
    """모니터 상태를 대시보드로 넘기는 공유 데이터 (스레드 안전)."""

    def __init__(self, repo: str, interval: int, slack: str):
        self.lock = threading.Lock()
        self.data = {
            "repo": repo,
            "interval": interval,
            "slack": slack,
            "polled_at": None,
            "fails": 0,
            "error": "",
            "issues": [],
            "prs": [],
            "events": [],
        }

    def update(self, **kw) -> None:
        with self.lock:
            self.data.update(kw)

    def set_snapshot(self, snap: dict) -> None:
        issues = [dict(v, number=int(k)) for k, v in snap["issues"].items()]
        prs = [dict(v, number=int(k)) for k, v in snap["prs"].items()]
        self.update(
            issues=sorted(issues, key=lambda x: -x["number"]),
            prs=sorted(prs, key=lambda x: -x["number"]),
            polled_at=_now_iso(),
            fails=0,
            error="",
        )

    def add_events(self, lines: list) -> None:
        ts = _now_iso()
        with self.lock:
            for ln in reversed(lines):
                self.data["events"].insert(0, {"ts": ts, "text": plain(ln), "url": first_url(ln)})
            del self.data["events"][EVENT_LIMIT:]

    def snapshot_json(self) -> bytes:
        with self.lock:
            return json.dumps(self.data, ensure_ascii=False).encode()


def start_server(dash: Dash, port: int):
    """127.0.0.1 에만 바인딩한다. Host 헤더가 localhost 가 아니면 거부한다 (DNS 리바인딩 방어).

    GET 만 지원한다.
    """

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _send(self, code: int, ctype: str, body: bytes) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'none'; script-src 'unsafe-inline'; "
                "style-src 'unsafe-inline'; connect-src 'self'",
            )
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if (self.headers.get("Host") or "").rsplit(":", 1)[0] not in (
                "127.0.0.1",
                "localhost",
            ):
                return self._send(403, "text/plain; charset=utf-8", b"forbidden")
            path = self.path.split("?")[0]
            if path == "/":
                try:
                    return self._send(200, "text/html; charset=utf-8", HTML_PATH.read_bytes())
                except OSError:
                    return self._send(500, "text/plain; charset=utf-8", b"dashboard html missing")
            if path == "/api/state":
                return self._send(200, "application/json; charset=utf-8", dash.snapshot_json())
            return self._send(404, "text/plain; charset=utf-8", b"not found")

    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


# ---------- GitHub / Slack I/O ----------


def gh(*args, timeout: int = 60) -> str:
    return subprocess.run(
        ["gh", *args], capture_output=True, text=True, check=True, timeout=timeout
    ).stdout


def git_root():
    r = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def fetch_claims(root) -> dict:
    """claim/<번호> ref → 소유자. scripts/claim.sh 가 커밋 제목 첫 단어에 로그인을 적는다.

    실패하면 빈 값을 돌려준다.
    """
    if not root:
        return {}
    r = subprocess.run(
        ["git", "-C", root, "ls-remote", "origin", "refs/heads/claim/*"],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0 or not r.stdout.strip():
        return {}
    subprocess.run(
        [
            "git",
            "-C",
            root,
            "fetch",
            "-q",
            "origin",
            "refs/heads/claim/*:refs/remotes/origin/claim/*",
        ],
        capture_output=True,
    )
    out = {}
    for line in r.stdout.strip().splitlines():
        sha, ref = line.split("\t")
        s = subprocess.run(
            ["git", "-C", root, "log", "-1", "--format=%s", sha], capture_output=True, text=True
        )
        out[ref.rsplit("/", 1)[-1]] = (s.stdout.strip().split(" ") or [""])[0]
    return out


def main_ci_status(repo: str, sha: str) -> str:
    """머지 커밋의 push 이벤트 워크플로 결과: pending | success | failure | none."""
    try:
        runs = json.loads(
            gh("api", f"repos/{repo}/actions/runs?head_sha={sha}&event=push&per_page=20")
        )["workflow_runs"]
    except (subprocess.SubprocessError, ValueError, KeyError):
        return "none"
    ci = [r for r in runs if r.get("name") == "CI"] or runs
    if not ci:
        return "none"
    if any(r["status"] != "completed" for r in ci):
        return "pending"
    return (
        "failure"
        if any(r["conclusion"] in ("failure", "timed_out", "startup_failure") for r in ci)
        else "success"
    )


def is_recent(iso, hours: int = 24, now=None) -> bool:
    """ISO8601(Z) 시각이 최근 hours 시간 안인가. 읽지 못하면 False."""
    try:
        t = datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)  # noqa: UP017
    except (TypeError, ValueError):
        return False
    now = now or datetime.now(timezone.utc)  # noqa: UP017
    return (now - t).total_seconds() < hours * 3600


def take_snapshot(repo: str, root, old_state: dict) -> dict:
    raw = json.loads(
        gh(
            "api",
            f"repos/{repo}/issues?state=all&sort=updated&direction=desc&per_page=100",
        )
    )
    claims = fetch_claims(root)
    issues = {}
    for i in raw:
        if "pull_request" in i:
            continue
        issues[str(i["number"])] = issue_entity(
            {
                "title": i["title"],
                "url": i["html_url"],
                "state": i["state"],
                "reason": i.get("state_reason"),
                "labels": [lb["name"] for lb in i["labels"]],
                "assignees": [a["login"] for a in i["assignees"]],
                "comments": i["comments"],
                "closed_by": ((i.get("closed_by") or {}).get("login") or ""),
                "assoc": i["author_association"],
                "author": i["user"]["login"],
            },
            claims.get(str(i["number"])),
        )
    prs_raw = json.loads(
        gh(
            "pr",
            "list",
            "--state",
            "all",
            "--limit",
            "50",
            "--json",
            "number,title,state,mergedAt,mergeCommit,headRefName,body,url,statusCheckRollup,author,mergedBy",
        )
    )
    prs = {}
    for p in prs_raw:
        old = old_state.get("prs", {}).get(str(p["number"]), {})
        ci = old.get("main_ci", "none")
        # main CI 는 최근 24시간 안에 머지된 PR 만 조회한다 (첫 실행에 수십 번 호출하지 않게)
        if is_recent(p.get("mergedAt")) and ci not in ("success", "failure"):
            ci = main_ci_status(repo, p["mergeCommit"]["oid"])
        prs[str(p["number"])] = pr_entity(p, ci)
    return {"issues": issues, "prs": prs}


def make_comment_fetcher(repo: str):
    def fetch(n: int, added: int) -> list:
        try:
            rows = json.loads(gh("api", f"repos/{repo}/issues/{n}/comments?per_page=100"))
        except (subprocess.SubprocessError, ValueError):
            return []
        rows = [c for c in rows if "<!-- ticket-agent -->" not in (c.get("body") or "")][-added:]
        return [
            {
                "user": c["user"]["login"],
                "assoc": c["author_association"],
                "body": c.get("body") or "",
            }
            for c in rows
        ]

    return fetch


def load_webhook():
    url = os.environ.get("SLACK_WEBHOOK_URL", "").strip()
    if not url:
        f = Path.home() / ".config" / "hackathon-kt" / "slack-webhook"
        url = f.read_text().strip() if f.exists() else ""
    return url if WEBHOOK_RE.match(url) else ""


def make_sender(webhook: str, dry_run: bool):
    def send(lines: list) -> bool:
        text = "\n".join(lines[:20]) + (f"\n… 외 {len(lines) - 20}건" if len(lines) > 20 else "")
        if dry_run:
            print("[dry-run → Slack]\n" + text + "\n", flush=True)
            return True
        req = urllib.request.Request(
            webhook,
            data=json.dumps({"text": text}).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return 200 <= r.status < 300
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            print(
                f"Slack 전송 실패: {type(e).__name__}", file=sys.stderr, flush=True
            )  # URL 은 찍지 않는다
            return False

    return send


def load_state(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent))
    with os.fdopen(fd, "w") as f:
        json.dump(state, f, ensure_ascii=False)
    os.replace(tmp, str(path))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="GitHub Issue 진행 상태 → Slack")
    ap.add_argument("--interval", type=int, default=30)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--quiet-start", action="store_true")
    ap.add_argument("--repo")
    ap.add_argument("--state-file")
    ap.add_argument("--serve", action="store_true")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-slack", action="store_true")
    ap.add_argument("--open", action="store_true")
    a = ap.parse_args(argv)

    webhook = load_webhook()
    if not webhook and not a.dry_run and not a.no_slack:
        print(
            "❌ Slack webhook 이 없다: SLACK_WEBHOOK_URL 또는 "
            "~/.config/hackathon-kt/slack-webhook "
            "(https://hooks.slack.com/services/…). Slack 없이 쓰려면 --no-slack",
            file=sys.stderr,
        )
        return 2
    try:
        repo = (
            a.repo
            or gh("repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner").strip()
        )
    except (subprocess.SubprocessError, OSError):
        print("❌ gh 로그인·저장소를 확인하지 못했다 (gh auth status)", file=sys.stderr)
        return 2
    slug = repo.replace("/", "_")
    path = Path(
        a.state_file
        or os.environ.get("ISSUE_MONITOR_STATE")
        or Path.home() / ".cache" / "hackathon-kt" / (f"issue-monitor-{slug}.json")
    )
    root, fetch_comments = git_root(), make_comment_fetcher(repo)
    real_send = make_sender(webhook, a.dry_run)
    state = load_state(path)
    dash = Dash(repo, a.interval, "off" if a.no_slack else ("dry-run" if a.dry_run else "on"))
    dash.update(events=list(state.get("events", [])))

    def send(lines: list) -> bool:
        ok = True if a.no_slack else real_send(lines)
        if ok:
            dash.add_events(lines)
        elif not a.dry_run:
            dash.update(slack="error")
        return ok

    if a.serve:
        try:
            _srv, port = start_server(dash, a.port)
        except OSError as e:
            print(f"❌ 대시보드 포트 {a.port} 를 열지 못했다: {e}", file=sys.stderr)
            return 2
        print(f"대시보드: http://127.0.0.1:{port}", flush=True)
        if a.open:
            webbrowser.open(f"http://127.0.0.1:{port}")
    fails, alerted, delay = 0, False, a.interval
    print(
        f"모니터 시작: {repo} · {a.interval}초마다 · 상태 {path}"
        + (" · dry-run" if a.dry_run else ""),
        flush=True,
    )
    while True:
        try:
            snap = take_snapshot(repo, root, state)
            if alerted:
                send(["✅ GitHub 조회 복구"])
            fails, alerted, delay = 0, False, a.interval
            dash.set_snapshot(snap)
            state = run_cycle(state, snap, send, fetch_comments, a.quiet_start)
            state["events"] = dash.data["events"][:EVENT_LIMIT]
            save_state(path, state)
        except (subprocess.SubprocessError, OSError, ValueError, KeyError) as e:
            fails += 1
            msg = getattr(e, "stderr", "") or str(e) or type(e).__name__
            dash.update(fails=fails, error=esc(msg, 200))
            print(f"조회 실패({fails}): {esc(msg, 200)}", file=sys.stderr, flush=True)
            delay = (
                min(300, a.interval * 2 ** min(fails, 4))
                if "rate limit" in msg.lower()
                else a.interval
            )
            if fails >= MAX_FAILS_BEFORE_ALERT and not alerted:
                alerted = send([f"⚠️ GitHub 조회가 {fails}번 연속 실패 — {esc(msg, 100)}"])
        if a.once:
            return 0
        try:
            time.sleep(delay)
        except KeyboardInterrupt:
            print("\n모니터 종료", flush=True)
            return 0


if __name__ == "__main__":
    sys.exit(main())
