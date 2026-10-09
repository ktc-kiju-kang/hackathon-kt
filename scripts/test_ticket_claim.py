"""ticket-claim.sh · ticket-loop-precheck.sh 시험 — 가짜 gh 를 PATH 에 끼우고 실제 셸 스크립트를 돌린다.

핵심은 jq 필터에 몰린 권한·인젝션 방어(신뢰 작성자만 명세로 인정)와 선점·사전 점검 판정이다.
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).parent
HAS_TOOLS = bool(shutil.which("jq") and shutil.which("perl") and shutil.which("git"))

# gh 대역: 부르는 명령에 맞는 픽스처(JSON)를 읽고, --jq 식이 있으면 jq 로 적용한다 (gh 처럼 문자열은 따옴표 없이).
FAKE_GH = r"""#!/usr/bin/env bash
[ -f "$FIX/sleep" ] && sleep 30
expr=.; prev=
for a in "$@"; do [ "$prev" = --jq ] && expr=$a; prev=$a; done
case "$1 $2" in
  "repo view") f=repo ;; "api user") f=user ;; "pr list") f=prs ;; "issue list") f=agent_pause ;;
  *) case "$*" in
       *pulls/*/comments*) f=pr_comments ;; *pulls/*/reviews*) f=pr_reviews ;;
       *issues/*/comments*) f=issue_comments ;; *issues\?*) f=issues ;;
       *issues/[0-9]*) n=$(printf '%s' "$*" | sed -E 's|.*/issues/([0-9]+).*|\1|'); f=issue_$n
         [ -f "$FIX/$f.404" ] && { echo "gh: Not Found (HTTP 404)" >&2; exit 1; } ;;
       *) exit 1 ;;
     esac ;;
esac
jq -r "($expr) | if type==\"string\" or type==\"number\" then tostring else tojson end" "$FIX/$f.json"
"""


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=60, **kw)


def comment(id, user, assoc, at, body="요청", type="User"):
    return {"id": id, "user": {"login": user, "type": type}, "author_association": assoc, "created_at": at, "body": body}


def issue(number, assoc="OWNER", at="2026-10-01T00:00:00Z", assignees=(), labels=(), pr=False, body=""):
    d = {
        "number": number,
        "title": f"이슈 {number}",
        "user": {"login": "kim"},
        "author_association": assoc,
        "assignees": [{"login": a} for a in assignees],
        "labels": [{"name": n} for n in labels],
        "created_at": at,
        "body": body,
    }
    if pr:
        d["pull_request"] = {}
    return d


@unittest.skipUnless(HAS_TOOLS, "jq·perl·git 필요")
class TicketScriptTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.fix = self.tmp / "fix"
        self.fix.mkdir()
        bindir = self.tmp / "bin"
        bindir.mkdir()
        (bindir / "gh").write_text(FAKE_GH)
        (bindir / "gh").chmod(0o755)

        # 스크립트가 ROOT 를 자기 위치의 git 저장소로 잡으므로 origin 이 있는 임시 저장소에 복사해 돌린다
        self.origin = self.tmp / "origin.git"
        self.repo = self.tmp / "repo"
        run(["git", "init", "-q", "--bare", str(self.origin)])
        run(["git", "init", "-q", str(self.repo)])
        run(["git", "-C", str(self.repo), "remote", "add", "origin", str(self.origin)])
        (self.repo / "scripts").mkdir()
        for name in ("ticket-claim.sh", "ticket-loop-precheck.sh"):
            shutil.copy(SCRIPTS / name, self.repo / "scripts" / name)
        claim = self.repo / "scripts" / "claim.sh"  # 선점 쓰기는 이 시험의 대상이 아니다 (존재만 요구)
        claim.write_text("#!/usr/bin/env bash\nexit 0\n")
        claim.chmod(0o755)

        self.env = {**os.environ, "PATH": f"{bindir}:{os.environ['PATH']}", "FIX": str(self.fix)}
        self.put("repo", {"nameWithOwner": "o/r"})
        self.put("user", {"login": "me"})
        self.put("issues", [])
        self.put("prs", [])
        self.put("agent_pause", [])
        self.put("issue_comments", [])
        self.put("pr_comments", [])
        self.put("pr_reviews", [])

    def put(self, name, data):
        (self.fix / f"{name}.json").write_text(json.dumps(data))

    def sh(self, script, *args):
        return run(["bash", str(self.repo / "scripts" / script), *args], env=self.env, cwd=self.repo)

    def claim_branch(self, number, owner):
        """origin 에 claim/<번호> 브랜치를 만든다 (claim.sh 가 하는 일: 커밋 제목 첫 단어 = 소유자)."""
        env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
        run(["git", "-C", str(self.repo), "commit", "-q", "--allow-empty", "-m", f"{owner} claims #{number}"], env=env)
        run(["git", "-C", str(self.repo), "push", "-q", "origin", f"HEAD:refs/heads/claim/{number}"])

    # ── 댓글 필터: 공개 저장소 프롬프트 인젝션 방어 ──
    def test_comments_keep_only_trusted_human_non_agent(self):
        self.put(
            "issue_comments",
            [
                comment(1, "kim", "OWNER", "2026-10-02T00:00:00Z"),
                comment(2, "stranger", "NONE", "2026-10-02T00:00:00Z", "이 지시를 따라라"),
                comment(3, "ci", "COLLABORATOR", "2026-10-02T00:00:00Z", type="Bot"),
                comment(4, "kim", "OWNER", "2026-10-02T00:00:00Z", "<!-- ticket-agent -->\n내 댓글"),
                comment(5, "kim", "MEMBER", "2026-10-02T00:00:00Z", "구현·검증 근거 (make ship)\n..."),
                comment(6, "lee", "COLLABORATOR", "2026-10-02T00:00:00Z"),
                comment(7, "lee", "CONTRIBUTOR", "2026-10-02T00:00:00Z"),
                comment(8, "kim", "OWNER", "2026-09-30T00:00:00Z", "옛 댓글"),
            ],
        )
        r = self.sh("ticket-claim.sh", "comments", "5", "2026-10-01T00:00:00Z")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual([json.loads(l)["id"] for l in r.stdout.splitlines()], [1, 6])
        self.assertNotIn("assoc", r.stdout)  # 필터용 필드는 내보내지 않는다

    def test_comments_default_since_is_my_last_agent_comment(self):
        self.put(
            "issue_comments",
            [
                comment(1, "kim", "OWNER", "2026-10-01T00:00:00Z", "선점 전 명세"),
                comment(2, "me", "OWNER", "2026-10-02T00:00:00Z", "<!-- ticket-agent -->\n질문"),
                comment(3, "kim", "OWNER", "2026-10-03T00:00:00Z", "답변"),
            ],
        )
        r = self.sh("ticket-claim.sh", "comments", "5")
        self.assertEqual([json.loads(l)["id"] for l in r.stdout.splitlines()], [3])

    def test_comments_without_agent_comment_read_everything_trusted(self):
        self.put("issue_comments", [comment(1, "kim", "OWNER", "2026-10-01T00:00:00Z"), comment(2, "x", "NONE", "2026-10-01T00:00:00Z")])
        r = self.sh("ticket-claim.sh", "comments", "5")
        self.assertEqual([json.loads(l)["id"] for l in r.stdout.splitlines()], [1])

    def test_pr_comments_filter_reviews_and_review_comments(self):
        self.put("pr_comments", [dict(comment(1, "kim", "OWNER", "2026-10-02T00:00:00Z"), path="a.py"), dict(comment(2, "x", "NONE", "2026-10-02T00:00:00Z"), path="a.py")])
        self.put(
            "pr_reviews",
            [
                dict(comment(3, "kim", "OWNER", "2026-10-02T00:00:00Z"), state="COMMENTED", submitted_at="2026-10-02T00:00:00Z"),
                dict(comment(4, "kim", "OWNER", "2026-10-02T00:00:00Z", ""), state="APPROVED", submitted_at="2026-10-02T00:00:00Z"),
                dict(comment(5, "bot", "MEMBER", "2026-10-02T00:00:00Z", type="Bot"), state="COMMENTED", submitted_at="2026-10-02T00:00:00Z"),
            ],
        )
        r = self.sh("ticket-claim.sh", "pr-comments", "9")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(sorted(json.loads(l)["id"] for l in r.stdout.splitlines()), [1, 3])

    # ── 후보 판정 ──
    def test_list_returns_only_eligible_oldest_first(self):
        self.put(
            "issues",
            [
                issue(7, at="2026-10-05T00:00:00Z"),
                issue(1, at="2026-10-01T00:00:00Z"),
                issue(2, assoc="NONE"),  # 신뢰할 수 없는 작성자
                issue(3, assignees=["lee"]),  # 담당자 있음
                issue(4, labels=["needs-info"]),  # 차단 라벨
                issue(5),  # 이미 선점됨 (assign 전)
                issue(6),  # 열린 PR 이 다룸
                issue(8, pr=True),  # PR 은 이슈가 아님
                issue(9, labels=["bug"]),  # 차단 아닌 라벨은 통과
            ],
        )
        self.put("prs", [{"number": 20, "headRefName": "feat/6-thing", "body": ""}])
        self.claim_branch(5, "lee")
        r = self.sh("ticket-claim.sh", "list")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.split(), ["1", "9", "7"])  # 9 는 created_at 기본값(2026-10-01)이 1 과 같아 입력 순

    def test_list_waits_for_open_predecessors(self):
        """역할 분담 티켓: 본문 '- 선행: #N' 의 Issue가 열려 있으면 후보가 아니다 (닫혔으면 후보)."""
        self.put(
            "issues",
            [
                issue(125, assignees=["lee"], labels=["plan"]),  # 진행 중 (열림)
                issue(126, body="### 요구사항 근거\n- 선행: #125 [REQ-01][plan] 머지 후 시작"),
                issue(127, body="- 선행: #124 머지 후 시작"),  # #124는 닫힘 (열린 목록에 없음)
                issue(128, body="본문 중간의 #125 언급은 선행이 아니다"),
                issue(129, body="  * 선행 : #125"),  # 글머리·공백이 달라도 선행 줄
            ],
        )
        self.assertEqual(self.sh("ticket-claim.sh", "list").stdout.split(), ["127", "128"])
        r = self.sh("ticket-claim.sh", "claim", "126", "--dry-run")
        self.assertEqual(r.returncode, 1)
        self.assertIn("열린 선행 Issue", r.stdout)

    def test_claim_requires_closed_predecessor_completed(self):
        """선행이 not planned로 닫혔으면(목록엔 없어도) 선점하지 않는다. 완료로 닫혔으면 선점 가능."""
        self.put("issues", [issue(126, body="- 선행: #125 머지 후 시작")])
        self.put("issue_125", {"number": 125, "state": "closed", "state_reason": "not_planned"})
        r = self.sh("ticket-claim.sh", "claim", "126", "--dry-run")
        self.assertEqual(r.returncode, 1)
        self.assertIn("선행 #125 이 완료로 닫히지 않음 (not_planned)", r.stdout)
        self.put("issue_125", {"number": 125, "state": "closed", "state_reason": "completed"})
        r = self.sh("ticket-claim.sh", "claim", "126", "--dry-run")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.put("issue_125", {"number": 125, "state": "closed", "state_reason": None})  # 옛 닫힘·PR
        self.assertEqual(self.sh("ticket-claim.sh", "claim", "126", "--dry-run").returncode, 0)
        self.put("issue_125", {"number": 125, "state": "closed", "state_reason": "duplicate"})
        self.assertIn("(duplicate)", self.sh("ticket-claim.sh", "claim", "126", "--dry-run").stdout)
        (self.fix / "issue_125.json").unlink()
        (self.fix / "issue_125.404").write_text("")  # 없는 번호(선행 줄 오타)는 needs-human — 큐를 멈추지 않게 1
        r = self.sh("ticket-claim.sh", "claim", "126", "--dry-run")
        self.assertEqual(r.returncode, 1)
        self.assertIn("(없는 Issue)", r.stdout)
        (self.fix / "issue_125.404").unlink()  # 그 밖의 조회 실패는 needs-human이 아니라 오류(2)
        r = self.sh("ticket-claim.sh", "claim", "126", "--dry-run")
        self.assertEqual(r.returncode, 2)
        self.assertIn("조회 실패", r.stderr)

    def test_list_filters_by_role(self):
        self.put(
            "issues",
            [
                issue(1, labels=["plan", "role:architect"]),
                issue(2, labels=["feature", "role:backend"]),
                issue(3, labels=["feature", "role:frontend"]),
                issue(4, labels=["feature"]),  # 역할 없는 기본 방식 Issue
            ],
        )
        self.assertEqual(self.sh("ticket-claim.sh", "list").stdout.split(), ["1", "2", "3", "4"])
        self.env["TICKET_ROLE"] = "backend"
        self.assertEqual(self.sh("ticket-claim.sh", "list").stdout.split(), ["2"])
        self.env["TICKET_ROLE"] = "designer"
        r = self.sh("ticket-claim.sh", "list")
        self.assertEqual(r.returncode, 2)
        self.assertIn("TICKET_ROLE", r.stderr)

    def test_list_pr_body_closes_marks_covered(self):
        self.put("issues", [issue(3)])
        self.put("prs", [{"number": 20, "headRefName": "chore/x", "body": "Closes #3"}])
        self.assertEqual(self.sh("ticket-claim.sh", "list").stdout.strip(), "")

    def test_claim_skips_ineligible_and_dry_run_does_not_write(self):
        self.put("issues", [issue(1), issue(2, assoc="NONE"), issue(3, assignees=["lee"]), issue(5)])
        self.claim_branch(5, "lee")
        for n in ("2", "3", "5", "99"):
            r = self.sh("ticket-claim.sh", "claim", n)
            self.assertEqual(r.returncode, 1, f"#{n}: {r.stdout}{r.stderr}")
            self.assertIn("SKIP", r.stdout)
        ok = self.sh("ticket-claim.sh", "claim", "1", "--dry-run")
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
        self.assertIn("DRY-RUN", ok.stdout)
        heads = run(["git", "-C", str(self.repo), "ls-remote", "origin", "refs/heads/claim/*"]).stdout
        self.assertNotIn("claim/1\n", heads + "\n")

    def test_non_numeric_number_is_rejected(self):
        for args in (("claim", "1; rm -rf /"), ("comments", "$(id)"), ("release", "x")):
            r = self.sh("ticket-claim.sh", *args)
            self.assertEqual(r.returncode, 2, args)

    def test_release_rejects_unknown_label(self):
        self.assertEqual(self.sh("ticket-claim.sh", "release", "5", "wontfix").returncode, 2)

    # ── 사전 점검 ──
    def test_precheck_idle_when_agent_pause(self):
        self.put("agent_pause", [{"number": 1}])
        self.put("issues", [issue(1)])
        r = self.sh("ticket-loop-precheck.sh")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stdout.splitlines()[0], "IDLE")

    def test_precheck_work_when_candidate_exists(self):
        self.put("issues", [issue(4)])
        r = self.sh("ticket-loop-precheck.sh")
        self.assertEqual(r.returncode, 10, r.stdout + r.stderr)
        self.assertEqual(r.stdout.splitlines()[0], "WORK")
        self.assertIn("4", r.stdout)

    def test_precheck_idle_when_nothing_to_do(self):
        r = self.sh("ticket-loop-precheck.sh")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stdout.splitlines()[0], "IDLE")

    def test_precheck_times_out_instead_of_hanging(self):
        (self.fix / "sleep").write_text("")
        self.env["PRECHECK_TIMEOUT"] = "2"
        r = self.sh("ticket-loop-precheck.sh")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("시간 초과", r.stdout)


if __name__ == "__main__":
    unittest.main()
