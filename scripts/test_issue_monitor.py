import importlib.util
import json
import tempfile
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

_spec = importlib.util.spec_from_file_location("im", Path(__file__).with_name("issue-monitor.py"))
im = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(im)


def issue(**kw):
    base = {
        "title": "제목",
        "url": "https://github.com/o/r/issues/1",
        "state": "open",
        "reason": "",
        "labels": [],
        "claim": "",
        "assignees": [],
        "comments": 0,
        "assoc": "OWNER",
        "author": "kim",
    }
    base.update(kw)
    return base


def pr(**kw):
    base = {
        "title": "PR",
        "url": "https://github.com/o/r/pull/9",
        "state": "open",
        "checks": "pending",
        "failing": [],
        "issues": [1],
        "merge_sha": "",
        "main_ci": "none",
    }
    base.update(kw)
    return base


class EscapeTest(unittest.TestCase):
    def test_mentions_and_links_are_neutralised(self):
        out = im.esc("<!channel> <@U123> <https://evil.example|click> & `x` *b*")
        self.assertNotIn("<", out)
        self.assertNotIn(">", out)
        self.assertIn("&lt;!channel&gt;", out)

    def test_limit_and_whitespace(self):
        self.assertEqual(len(im.esc("가" * 500, 50)), 51)
        self.assertNotIn("\n", im.esc("a\nb\r\nc"))

    def test_link_only_github(self):
        self.assertTrue(
            im.link("https://github.com/o/r/issues/1", "x").startswith("<https://github.com/")
        )
        self.assertNotIn("<", im.link("https://evil.example/x", "x"))

    def test_plain_roundtrip(self):
        line = "{} — 🔒 선점".format(im.link("https://github.com/o/r/issues/1", "A & B"))
        self.assertEqual(im.plain(line), "A & B — 🔒 선점")
        self.assertEqual(im.first_url(line), "https://github.com/o/r/issues/1")

    def test_plain_strips_bold_but_keeps_escaped_asterisk(self):
        head = im.link("https://github.com/o/r/pull/9", "T")
        line = f"{head} *PR #9* — 🎉 머지됨 · {im.esc('a*b*c')}"
        self.assertEqual(im.plain(line), "T PR #9 — 🎉 머지됨 · a*b*c")


class ChecksTest(unittest.TestCase):
    def test_summaries(self):
        ok = {"status": "COMPLETED", "conclusion": "SUCCESS", "name": "a"}
        bad = {"status": "COMPLETED", "conclusion": "FAILURE", "name": "b"}
        run = {"status": "IN_PROGRESS", "conclusion": "", "name": "c"}
        cancelled = {"status": "COMPLETED", "conclusion": "CANCELLED", "name": "d"}
        self.assertEqual(im.summarize_checks([]), ("none", []))
        self.assertEqual(im.summarize_checks([ok, cancelled]), ("success", []))
        self.assertEqual(im.summarize_checks([ok, bad]), ("failure", ["b"]))
        self.assertEqual(im.summarize_checks([ok, bad, run])[0], "pending")
        self.assertEqual(im.summarize_checks([cancelled]), ("none", []))

    def test_status_context(self):
        self.assertEqual(
            im.summarize_checks([{"state": "SUCCESS", "context": "Vercel"}])[0], "success"
        )
        self.assertEqual(
            im.summarize_checks([{"state": "PENDING", "context": "Vercel"}])[0], "pending"
        )
        self.assertEqual(
            im.summarize_checks([{"state": "FAILURE", "context": "Vercel"}]),
            ("failure", ["Vercel"]),
        )

    def test_linked_issues(self):
        p = {"headRefName": "feat/87-health", "body": "Closes #12 and fixes #13"}
        self.assertEqual(im.linked_issues(p), [12, 13, 87])
        self.assertEqual(im.linked_issues({"headRefName": "main", "body": None}), [])


class DiffIssueTest(unittest.TestCase):
    def fc(self, n, added):
        return [{"user": "bob", "assoc": "NONE", "body": "<!channel> 안녕"}]

    def test_new_open_issue_flags_outsiders(self):
        ev = im.diff_issue(5, None, issue(assoc="NONE", author="stranger"), self.fc)
        self.assertEqual(len(ev), 1)
        self.assertIn("외부 작성자", ev[0])
        self.assertEqual(im.diff_issue(5, None, issue(state="closed"), self.fc), [])

    def test_claim_release_and_labels(self):
        old, new = issue(), issue(claim="kim")
        self.assertIn("선점", im.diff_issue(1, old, new, self.fc)[0])
        self.assertIn("선점 해제", im.diff_issue(1, new, old, self.fc)[0])
        self.assertIn("사람 확인", im.diff_issue(1, old, issue(labels=["needs-info"]), self.fc)[0])
        self.assertIn("해제", im.diff_issue(1, issue(labels=["blocked"]), old, self.fc)[0])
        self.assertIn(
            "일시 정지", im.diff_issue(1, old, issue(labels=["agent-pause"]), self.fc)[0]
        )

    def test_closed_and_reopened(self):
        self.assertIn("완료", im.diff_issue(1, issue(), issue(state="closed"), self.fc)[0])
        self.assertIn(
            "계획 없음",
            im.diff_issue(1, issue(), issue(state="closed", reason="not_planned"), self.fc)[0],
        )
        self.assertIn("다시 열림", im.diff_issue(1, issue(state="closed"), issue(), self.fc)[0])

    def test_comment_is_escaped_and_marks_outsider(self):
        ev = im.diff_issue(1, issue(), issue(comments=1), self.fc)
        self.assertEqual(len(ev), 1)
        self.assertNotIn("<!channel>", ev[0])
        self.assertIn("외부", ev[0])

    def test_comment_fallback_when_fetch_fails(self):
        ev = im.diff_issue(1, issue(), issue(comments=2), lambda n, a: [])
        self.assertIn("새 댓글 2개", ev[0])

    def test_no_change_no_events(self):
        self.assertEqual(im.diff_issue(1, issue(), issue(), self.fc), [])


class DiffPrTest(unittest.TestCase):
    def test_lifecycle(self):
        self.assertIn("PR 열림", im.diff_pr(9, None, pr())[0])
        self.assertIn("체크 통과", im.diff_pr(9, pr(), pr(checks="success"))[0])
        self.assertIn("체크 실패", im.diff_pr(9, pr(), pr(checks="failure", failing=["lint"]))[0])
        self.assertIn("머지됨", im.diff_pr(9, pr(), pr(state="merged"))[0])
        self.assertIn("머지 안 됨", im.diff_pr(9, pr(), pr(state="closed"))[0])
        self.assertEqual(
            im.diff_pr(9, pr(checks="success"), pr(checks="pending")), []
        )  # 새 push: 조용히

    def test_main_ci(self):
        merged = pr(state="merged", merge_sha="abc1234")
        self.assertIn("main CI 통과", im.diff_pr(9, merged, dict(merged, main_ci="success"))[0])
        self.assertIn("main CI 실패", im.diff_pr(9, merged, dict(merged, main_ci="failure"))[0])


class ActorTest(unittest.TestCase):
    def test_pr_opened_shows_author(self):
        ev = im.diff_pr(9, None, pr(author="kim"))
        self.assertIn("PR 열림 · kim", ev[0])

    def test_merge_shows_merger_and_author_when_different(self):
        merged = pr(state="merged", author="kim", merged_by="kang")
        ev = im.diff_pr(9, pr(author="kim"), merged)
        self.assertIn("머지됨 · 머지 kang (작성 kim)", ev[0])

    def test_merge_shows_single_name_when_same(self):
        merged = pr(state="merged", author="kang", merged_by="kang")
        ev = im.diff_pr(9, pr(author="kang"), merged)
        self.assertIn("머지됨 · kang", ev[0])
        self.assertNotIn("작성", ev[0])

    def test_merge_without_actor_info_still_alerts(self):
        ev = im.diff_pr(9, pr(), pr(state="merged"))
        self.assertTrue(ev[0].endswith("🎉 머지됨 (이슈 #1)"))

    def test_issue_closed_shows_who(self):
        ev = im.diff_issue(1, issue(), issue(state="closed", closed_by="kang"), lambda n, a: [])
        self.assertIn("✅ 닫힘 (완료) · kang", ev[0])
        ev = im.diff_issue(1, issue(), issue(state="closed"), lambda n, a: [])
        self.assertTrue(ev[0].endswith("✅ 닫힘 (완료)"))

    def test_actor_names_are_escaped(self):
        ev = im.diff_pr(9, None, pr(author="<!channel>"))
        self.assertNotIn("<!channel>", ev[0])

    def test_old_state_without_actor_fields_is_silent(self):
        # 업그레이드 직후: 필드만 새로 생긴 변화는 알림 없이 상태만 갱신한다
        old_pr = {k: v for k, v in pr().items() if k not in ("author", "merged_by")}
        state = {"init": True, "issues": {}, "prs": {"9": old_pr}}
        snap = {"issues": {}, "prs": {"9": pr(author="kim")}}
        sent = []
        st = im.run_cycle(state, snap, lambda lines: sent.append(lines) or True, lambda *a: [])
        self.assertEqual(sent, [])
        self.assertEqual(st["prs"]["9"]["author"], "kim")


class WatchTest(unittest.TestCase):
    def test_load_watch_filters_and_dedupes(self):
        got = im.load_watch(["a/b", "a/b", "bad", "o/r", "x/y z"], "o/r")
        self.assertEqual(got[0], "a/b")
        self.assertNotIn("o/r", got)
        self.assertNotIn("bad", got)
        self.assertEqual(got.count("a/b"), 1)

    def test_set_other_in_state_json(self):
        dash = im.Dash("o/r", 30, "off")
        dash.set_other("a/b", {"issues": {"3": issue()}, "prs": {"7": pr()}})
        data = json.loads(dash.snapshot_json())
        self.assertEqual(data["others"]["a/b"]["issues"][0]["number"], 3)
        self.assertEqual(data["others"]["a/b"]["prs"][0]["number"], 7)

    def test_watch_entities_only_produce_lifecycle_events(self):
        # 감시 모드는 댓글·라벨·선점·체크가 상수라 새 이슈/PR/머지/닫힘만 알림이 난다
        old = issue(comments=0, labels=[], claim="")
        self.assertEqual(im.diff_issue(1, old, dict(old), lambda *a: []), [])
        self.assertIn("새 이슈", im.diff_issue(2, None, issue(), lambda *a: [])[0])
        merged = pr(state="merged", checks="none")
        self.assertIn("머지됨", im.diff_pr(9, pr(checks="none"), merged)[0])


class CycleTest(unittest.TestCase):
    def snap(self, **kw):
        return {"issues": kw.get("issues", {}), "prs": kw.get("prs", {})}

    def test_first_run_is_baseline_with_one_start_message(self):
        sent = []
        st = im.run_cycle(
            {},
            self.snap(issues={"1": issue()}),
            lambda lines: sent.append(lines) or True,
            lambda *a: [],
        )
        self.assertTrue(st["init"])
        self.assertEqual(len(sent), 1)
        self.assertIn("시작", sent[0][0])
        quiet = []
        im.run_cycle(
            {},
            self.snap(),
            lambda lines: quiet.append(lines) or True,
            lambda *a: [],
            quiet_start=True,
        )
        self.assertEqual(quiet, [])

    def test_changes_are_batched_into_one_message(self):
        state = {"init": True, "issues": {"1": issue()}, "prs": {}}
        snap = self.snap(issues={"1": issue(claim="kim"), "2": issue(title="새")}, prs={"9": pr()})
        sent = []
        st = im.run_cycle(state, snap, lambda lines: sent.append(lines) or True, lambda *a: [])
        self.assertEqual(len(sent), 1)
        self.assertEqual(len(sent[0]), 3)
        self.assertEqual(st["issues"]["1"]["claim"], "kim")

    def test_failed_send_keeps_old_state_for_retry(self):
        state = {"init": True, "issues": {"1": issue()}, "prs": {}}
        snap = self.snap(issues={"1": issue(claim="kim")})
        st = im.run_cycle(state, snap, lambda lines: False, lambda *a: [])
        self.assertEqual(st["issues"]["1"]["claim"], "")  # 아직 안 보냈으니 옛 상태 → 다음에 다시
        sent = []
        st2 = im.run_cycle(st, snap, lambda lines: sent.append(lines) or True, lambda *a: [])
        self.assertEqual(len(sent), 1)
        self.assertEqual(st2["issues"]["1"]["claim"], "kim")

    def test_silent_change_is_absorbed(self):
        state = {"init": True, "issues": {"1": issue()}, "prs": {}}
        snap = self.snap(issues={"1": issue(title="제목 수정")})
        sent = []
        st = im.run_cycle(state, snap, lambda lines: sent.append(lines) or True, lambda *a: [])
        self.assertEqual(sent, [])
        self.assertEqual(st["issues"]["1"]["title"], "제목 수정")


class WebhookTest(unittest.TestCase):
    def test_validation(self):
        import os

        old = os.environ.get("SLACK_WEBHOOK_URL")
        try:
            os.environ["SLACK_WEBHOOK_URL"] = "https://evil.example/hook"
            self.assertEqual(im.load_webhook(), "") if not (
                Path.home() / ".config/hackathon-kt/slack-webhook"
            ).exists() else None
            os.environ["SLACK_WEBHOOK_URL"] = "https://hooks.slack.com/services/T000/B000/XXXX"
            self.assertTrue(im.load_webhook())
        finally:
            if old is None:
                os.environ.pop("SLACK_WEBHOOK_URL", None)
            else:
                os.environ["SLACK_WEBHOOK_URL"] = old

    def test_sender_failure_does_not_leak_url(self):
        import contextlib
        import io

        buf = io.StringIO()
        secret = "https://hooks.slack.com/services/T000/B000/SECRETSECRET"
        send = im.make_sender(secret, False)
        orig = urllib.request.urlopen
        urllib.request.urlopen = lambda *a, **k: (_ for _ in ()).throw(
            urllib.error.URLError("boom " + secret)
        )
        try:
            with contextlib.redirect_stderr(buf):
                self.assertFalse(send(["x"]))
        finally:
            urllib.request.urlopen = orig
        self.assertNotIn("SECRETSECRET", buf.getvalue())


class RecentTest(unittest.TestCase):
    def test_is_recent(self):
        now = datetime(2026, 10, 8, 12, 0, 0, tzinfo=timezone.utc)  # noqa: UP017 (3.9 호환)
        self.assertTrue(im.is_recent("2026-10-08T08:03:49Z", now=now))
        self.assertTrue(im.is_recent("2026-10-07T12:00:01Z", now=now))
        self.assertFalse(im.is_recent("2026-10-07T11:59:59Z", now=now))
        self.assertFalse(im.is_recent(None, now=now))
        self.assertFalse(im.is_recent("garbage", now=now))


class StateFileTest(unittest.TestCase):
    def test_roundtrip_and_missing(self):
        d = Path(tempfile.mkdtemp())
        self.assertEqual(im.load_state(d / "none.json"), {})
        im.save_state(d / "sub" / "s.json", {"init": True, "x": "한글"})
        self.assertEqual(im.load_state(d / "sub" / "s.json")["x"], "한글")


class DashboardServerTest(unittest.TestCase):
    def setUp(self):
        self.dash = im.Dash("o/r", 30, "off")
        self.dash.set_snapshot({"issues": {"1": issue()}, "prs": {"9": pr()}})
        self.dash.add_events(
            ["{} — 🔒 선점".format(im.link("https://github.com/o/r/issues/1", "T"))]
        )
        self.srv, self.port = im.start_server(self.dash, 0)

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()

    def get(self, path, host=None):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}")
        if host:
            req.add_header("Host", host)
        return urllib.request.urlopen(req, timeout=5)

    def test_state_json(self):
        r = self.get("/api/state")
        self.assertEqual(r.status, 200)
        self.assertIn("no-store", r.headers["Cache-Control"])
        data = json.loads(r.read())
        self.assertEqual(data["repo"], "o/r")
        self.assertEqual(data["issues"][0]["number"], 1)
        self.assertEqual(data["events"][0]["text"], "T — 🔒 선점")

    def test_html_served(self):
        r = self.get("/")
        self.assertEqual(r.status, 200)
        self.assertIn("text/html", r.headers["Content-Type"])
        self.assertIn("default-src 'none'", r.headers["Content-Security-Policy"])
        body = r.read().decode()
        import re

        # 외부 입력은 textContent 로만: HTML 직접 삽입 API 는 금지 (주석의 언급은 허용)
        self.assertIsNone(
            re.search(r"\.(innerHTML|outerHTML)\b|insertAdjacentHTML|document\.write", body)
        )

    def test_foreign_host_rejected(self):
        with self.assertRaises(urllib.error.HTTPError) as cm:
            self.get("/api/state", host="evil.example")
        self.assertEqual(cm.exception.code, 403)

    def test_404_and_no_post(self):
        with self.assertRaises(urllib.error.HTTPError) as cm:
            self.get("/nope")
        self.assertEqual(cm.exception.code, 404)
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/state", data=b"x", method="POST"
        )
        with self.assertRaises(urllib.error.HTTPError):
            urllib.request.urlopen(req, timeout=5)

    def test_event_limit(self):
        self.dash.add_events([f"e{i}" for i in range(250)])
        self.assertEqual(len(self.dash.data["events"]), im.EVENT_LIMIT)


if __name__ == "__main__":
    unittest.main()
