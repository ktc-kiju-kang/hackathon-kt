"""ticket-claim.sh · ticket-loop-precheck.sh · lib.sh 머지 게이트(머지 조건·스키마 G3) 시험 — 가짜 gh 를 PATH 에 끼우고 실제 셸 스크립트를 돌린다.

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
for a in "$@"; do { [ "$prev" = --jq ] || [ "$prev" = -q ]; } && expr=$a; prev=$a; done
case "$1 $2" in
  "repo view") f=repo ;; "api user") f=user ;; "pr list") f=prs ;; "issue list") f=agent_pause ;;
  "pr view") f=pr_view ;;
  "issue comment"|"issue edit"|"label create") exit 0 ;;  # 쓰기 명령은 성공한 것으로
  "pr checks") f=pr_checks; [ -f "$FIX/pr_checks.nochecks" ] && { echo "no checks reported on the 'x' branch" >&2; exit 1; }  # $FIX/seq 가 있으면 한 줄씩 꺼내 쓴다 (pending → pass 같은 흐름)
    if [ -s "$FIX/seq" ]; then f=$(head -1 "$FIX/seq"); tail -n +2 "$FIX/seq" >"$FIX/seq.tmp"; mv "$FIX/seq.tmp" "$FIX/seq"; fi ;;
  "issue view") f=issue_$3; [ -f "$FIX/$f.404" ] && { echo "gh: Not Found (HTTP 404)" >&2; exit 1; }
    # REAL_GH: --jq 식을 진짜 gh 내장 jq(gojq)로 평가한다 — 픽스처를 jq 리터럴로 넣고 가벼운 API 응답은 버린다
    [ -n "${REAL_GH:-}" ] && exec "$REAL_GH" api rate_limit --jq "$(cat "$FIX/$f.json") | $expr" ;;
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
        for name in ("ticket-claim.sh", "ticket-loop-precheck.sh", "lib.sh", "ticket-tick.sh"):
            shutil.copy(SCRIPTS / name, self.repo / "scripts" / name)
        claim = self.repo / "scripts" / "claim.sh"  # 선점 쓰기는 이 시험의 대상이 아니다 (존재만 요구)
        claim.write_text("#!/usr/bin/env bash\nexit 0\n")
        claim.chmod(0o755)

        # 루프 세션의 TICKET_ROLE 등이 시험에 섞이지 않게 뺀다 (역할 루프 안에서 make verify를 돌려도 같은 결과)
        base = {k: v for k, v in os.environ.items() if not k.startswith("TICKET_")}
        self.env = {**base, "PATH": f"{bindir}:{os.environ['PATH']}", "FIX": str(self.fix)}
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
        self.put("issue_125", {"number": 125, "state": "open"})  # 열린 PR 번호·다시 열림 → 대기만
        r = self.sh("ticket-claim.sh", "claim", "126", "--dry-run")
        self.assertIn("선행 #125 열림 — 대기", r.stdout)
        self.assertNotIn("needs-human", r.stdout)
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

    def test_claim_rejects_bare_predecessor_numbers(self):
        """티켓 초안의 '- 선행: 04, 02'가 #번호로 안 바뀐 채 Issue가 되면 의존 없음으로 통과시키지 않는다."""
        self.put("issues", [issue(9, body="- 선행: 04, 02 머지 후 시작\n- 참고: [REQ-01][plan]")])
        r = self.sh("ticket-claim.sh", "claim", "9", "--dry-run")
        self.assertEqual(r.returncode, 1)
        self.assertIn("'#' 없는 번호", r.stdout)
        self.put("issues", [issue(9, body="- 선행: #10, 04")])  # 일부만 바뀐 줄도
        self.assertIn("'#' 없는 번호", self.sh("ticket-claim.sh", "claim", "9", "--dry-run").stdout)
        self.put("issue_10", {"number": 10, "state": "closed", "state_reason": "completed"})
        for body in ("- 선행: 없음\n- 참고: 04 [REQ-01][plan]", "- 선행: #10 [REQ-01][plan] (2개 중 1)", "- 선행: #10 REQ-01 머지 후"):
            self.put("issues", [issue(9, body=body)])  # 없음·참고 줄·괄호 설명·REQ-ID는 괜찮다
            self.assertEqual(self.sh("ticket-claim.sh", "claim", "9", "--dry-run").returncode, 0, body)

    def test_merge_wait_reads_only_merge_condition_lines(self):
        """FE의 '- 머지 조건:'(같은 REQ의 BE)이 완료로 닫히기 전에는 머지하지 않는다 — 선행과 같은 기준."""
        body = "- 선행: #10\n- 머지 조건: #11 (같은 REQ의 BE)\n  * 머지 조건 : #13\n- 참고: #14 [REQ-01][BE]"
        self.put("issue_12", {"number": 12, "state": "open", "body": body})
        self.put("issue_11", {"number": 11, "state": "closed", "state_reason": "completed"})
        self.put("issue_13", {"number": 13, "state": "closed", "state_reason": None})  # 옛 닫힘 = 완료
        r = self.sh("ticket-claim.sh", "merge-wait", "12")
        self.assertEqual((r.returncode, r.stdout), (0, ""), r.stderr)  # 선행 #10·참고 #14(픽스처 없음)는 보지 않는다
        self.put("issue_11", {"number": 11, "state": "open"})
        r = self.sh("ticket-claim.sh", "merge-wait", "12")
        self.assertEqual(r.returncode, 1)
        self.assertEqual(r.stdout.strip(), "#11 아직 열림 — 먼저 머지된 뒤")
        self.put("issue_11", {"number": 11, "state": "closed", "state_reason": "not_planned"})
        self.assertIn("#11 이 완료로 닫히지 않음 (not_planned)", self.sh("ticket-claim.sh", "merge-wait", "12").stdout)
        (self.fix / "issue_11.json").unlink()  # 조회 실패도 머지하지 않는다 (이유를 보인다)
        self.assertIn("#11 조회 실패", self.sh("ticket-claim.sh", "merge-wait", "12").stdout)
        self.put("issue_12", {"number": 12, "state": "open", "body": "- 머지 조건: 11 [REQ-01][BE]"})  # NN이 안 바뀜
        r = self.sh("ticket-claim.sh", "merge-wait", "12")
        self.assertEqual(r.returncode, 1)
        self.assertIn("'#' 없는 번호", r.stdout)
        self.put("issue_12", {"number": 12, "state": "open", "body": "- 머지조건: #11"})  # 띄어쓰기가 달라도 읽는다
        self.assertIn("#11 조회 실패", self.sh("ticket-claim.sh", "merge-wait", "12").stdout)
        self.put("issue_12", {"number": 12, "state": "open", "body": None})  # 본문 없음·머지 조건 없음
        self.assertEqual(self.sh("ticket-claim.sh", "merge-wait", "12").returncode, 0)

    def test_merge_wait_without_line_needs_no_repo_lookup(self):
        """머지 조건 줄이 없는 Issue는 저장소·계정 확인이 실패해도 make ship을 막지 않는다."""
        (self.fix / "repo.json").unlink()
        (self.repo / "scripts" / "claim.sh").unlink()  # 선점 도구도 묻지 않는다
        self.env["TICKET_ROLE"] = "designer"  # 루프용 역할 값이 셸에 남아 있어도
        self.put("issue_12", {"number": 12, "state": "open", "body": "- 선행: #10"})
        self.assertEqual(self.sh("ticket-claim.sh", "merge-wait", "12").returncode, 0)
        self.put("issue_12", {"number": 12, "state": "open", "body": "- 머지 조건: #11"})
        self.assertEqual(self.sh("ticket-claim.sh", "merge-wait", "12").returncode, 2)  # 줄이 있으면 확인이 필요하다
        self.assertEqual(self.sh("ticket-claim.sh", "list").returncode, 2)

    def test_merge_wait_same_under_gh_builtin_jq(self):
        """merge-wait의 본문 해석은 실제로 gh 내장 jq(gojq, RE2)에서 돈다 — 시스템 jq(oniguruma)와 결과가 같아야 한다."""
        real_gh = shutil.which("gh")  # 로그인된 gh가 GitHub에 닿을 때만 (로컬 make verify·make ship). 오프라인·CI는 건너뛴다
        if not real_gh or run([real_gh, "api", "rate_limit", "--jq", ".rate.limit"]).returncode != 0:
            self.skipTest("GitHub에 닿는 로그인된 gh 필요")
        self.put("issue_11", {"number": 11, "state": "open"})
        bodies = [
            "- 선행: #10\n- 머지 조건: #11 (같은 REQ의 BE)\n  * 머지조건 : #13",
            "- 머지 조건: 11 [REQ-01][BE]",
            "- 머지 조건: #11, 04",
            "\t-\t머지 조건\t: #11",
            "- 머지 조건: 없음",
            "본문 - 머지 조건: #11 (줄 머리 아님)",
            None,
        ]
        for body in bodies:
            self.put("issue_12", {"number": 12, "state": "open", "body": body})
            plain = self.sh("ticket-claim.sh", "merge-wait", "12")
            real = run(["bash", str(self.repo / "scripts" / "ticket-claim.sh"), "merge-wait", "12"],
                       env={**self.env, "REAL_GH": real_gh}, cwd=self.repo)
            self.assertEqual((real.returncode, real.stdout), (plain.returncode, plain.stdout), f"{body!r}: {real.stderr}")
            self.assertIn(plain.returncode, (0, 1), plain.stderr)

    def ship_gate(self, issue, no_merge):
        """make ship의 머지 조건 분기 (lib.sh merge_waiting → PR 본문 이유, merge_gate → 경고 또는 멈춤)."""
        env = {**self.env, "SHIP_NO_MERGE": "1" if no_merge else ""}
        script = f'. scripts/lib.sh; w=$(merge_waiting {issue}); echo "W[$w]"; merge_gate "$w" 99; echo MERGE'
        return run(["bash", "-c", script], env=env, cwd=self.repo)

    def test_ship_merge_gate_warns_or_stops(self):
        self.put("issue_12", {"number": 12, "state": "open", "body": "- 머지 조건: #11"})
        self.put("issue_11", {"number": 11, "state": "open"})
        r = self.ship_gate(12, no_merge=True)  # 머지는 사람: PR 본문에 적고 경고만
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("W[#11 아직 열림 — 먼저 머지된 뒤]", r.stdout)
        self.assertIn("머지 조건이 풀리지 않음", r.stdout)
        self.assertIn("MERGE", r.stdout)
        r = self.ship_gate(12, no_merge=False)  # 머지까지 맡긴 실행: 멈춘다
        self.assertEqual(r.returncode, 1)
        self.assertNotIn("MERGE", r.stdout)
        self.assertIn("PR #99 은 그대로 둠", r.stderr)
        self.put("issue_11", {"number": 11, "state": "closed", "state_reason": "completed"})
        r = self.ship_gate(12, no_merge=False)  # 풀렸으면 그대로 머지로
        self.assertEqual((r.returncode, r.stdout.split()), (0, ["W[]", "MERGE"]), r.stderr)
        (self.fix / "issue_12.404").write_text("")  # Issue 조회 실패 = 판정 실패, 머지하지 않는다
        r = self.ship_gate(12, no_merge=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn("W[판정 실패: ❌ Issue #12 조회 실패 — 다시 make ship]", r.stdout)
        (self.repo / "scripts" / "ticket-claim.sh").write_text("exit 2\n")  # 진단 없이 죽어도 원인 칸을 비우지 않는다
        self.assertIn("W[판정 실패: 종료코드 2 — 다시 make ship]", self.ship_gate(12, no_merge=True).stdout)

    def test_mine_fails_when_claim_list_fails(self):
        """선점 목록(ls-remote) 조회 실패는 '내 티켓 없음'이 아니다 — 틱이 새 티켓을 잡지 않게."""
        self.git("remote", "set-url", "origin", str(self.tmp / "no-such.git"))
        self.assertNotEqual(self.sh("ticket-claim.sh", "mine").returncode, 0)

    def test_claim_checks_see_claims_that_are_not_last(self):
        """선점 확인이 뒤에 다른 선점이 있어도 보인다 (pipefail + grep -q SIGPIPE로 '없음'이 되던 회귀)."""
        for n in (2, 3, 4, 5):
            self.claim_branch(n, "me")
        self.put("issues", [issue(2)])
        r = self.sh("ticket-claim.sh", "claim", "2")
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("SKIP #2: 이미 선점됨 (me)", r.stdout)
        r = self.sh("ticket-claim.sh", "release", "2")  # 시험용 claim.sh는 지우지 않는다 → 남은 선점을 알아채야 한다
        self.assertEqual(r.returncode, 2)
        self.assertIn("#2 선점이 남아 있음", r.stderr)
        self.assertNotIn("RELEASED", r.stdout)

    def test_mine_filters_by_role(self):
        """한 계정에서 역할 루프를 여럿 돌려도 다른 역할의 선점을 '내 진행 중'으로 보고 멈추지 않는다."""
        self.claim_branch(3, "me")
        self.claim_branch(5, "me")
        self.claim_branch(7, "other")
        self.put("issue_3", {"number": 3, "state": "OPEN", "labels": [{"name": "role:backend"}]})
        self.put("issue_5", {"number": 5, "state": "OPEN", "labels": [{"name": "feature"}, {"name": "role:frontend"}]})
        self.put("issue_7", {"number": 7, "state": "OPEN", "labels": [{"name": "role:backend"}]})
        self.assertEqual(self.sh("ticket-claim.sh", "mine").stdout.split(), ["3", "5"])
        self.env["TICKET_ROLE"] = "frontend"
        self.assertEqual(self.sh("ticket-claim.sh", "mine").stdout.split(), ["5"])
        self.env["TICKET_ROLE"] = "architect"
        self.assertEqual(self.sh("ticket-claim.sh", "mine").stdout.split(), [])
        self.put("issue_3", {"number": 3, "state": "CLOSED", "labels": [{"name": "role:backend"}]})
        self.env["TICKET_ROLE"] = "backend"
        self.assertEqual(self.sh("ticket-claim.sh", "mine").stdout.split(), [])

    def git(self, *args):
        env = {**self.env, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
        r = run(["git", "-C", str(self.repo), *args], env=env)
        self.assertEqual(r.returncode, 0, r.stderr)

    def write_commit(self, files, msg):
        for path, text in files.items():
            f = self.repo / path
            if text is None:
                f.unlink()
                continue
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(text)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", msg)

    def schema_gate(self, loop=True, no_merge=False):
        env = {**self.env, "TICKET_LOOP_MERGE": "1" if loop else "", "SHIP_NO_MERGE": "1" if no_merge else ""}
        return run(["bash", "-c", "set -uo pipefail; . scripts/lib.sh; schema_gate 99; echo MERGE"], env=env, cwd=self.repo)  # ship.sh와 같은 셸 옵션

    def test_schema_gate_stops_loop_merge_on_table_contracts(self):
        """G3: 루프 자동 머지에서 '## 테이블' 절이 있는 계약을 바꾸면 사람이 머지한다 (컬럼 한 줄만 바뀌어도)."""
        table = "# memo\n\n## 테이블 (SQL 초안)\n    CREATE TABLE memos (\n      id bigserial primary key\n    );\n"
        self.write_commit({"docs/contracts/memo.md": table, "docs/contracts/todo.md": "# todo\n", "docs/contracts/README.md": "# 계약\n"}, "base")
        self.git("push", "-q", "origin", "HEAD:refs/heads/main")
        self.git("fetch", "-q", "origin")
        self.git("switch", "-q", "-c", "feat/1-x")
        base = self.schema_gate()
        self.assertEqual((base.returncode, base.stdout.strip()), (0, "MERGE"), base.stderr)  # 계약 변경 없음

        self.write_commit({"docs/contracts/memo.md": table.replace("primary key", "primary key,\n      body text")}, "column")
        r = self.schema_gate()  # 루프 자동 머지 → 멈춘다
        self.assertEqual(r.returncode, 1)
        self.assertNotIn("MERGE", r.stdout)
        self.assertIn("docs/contracts/memo.md", r.stderr)
        self.assertIn("PR #99", r.stderr)
        r = self.schema_gate(no_merge=True)  # 머지는 사람 → 경고만
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("스키마를 확인하고 머지하세요", r.stdout)
        self.assertIn("MERGE", r.stdout)
        self.assertEqual(self.schema_gate(loop=False).returncode, 0)  # 사람이 직접 ship → 걸지 않는다
        self.env["SHIP_KIND"] = "record"
        self.assertEqual(self.schema_gate().returncode, 0)  # 기록 PR(make record)도 걸지 않는다
        del self.env["SHIP_KIND"]

        self.git("reset", "-q", "--hard", "origin/main")
        self.write_commit({"docs/contracts/todo.md": "# todo\n- 사용처: 목록\n", "docs/contracts/README.md": "# 계약\n## 테이블 (SQL 초안)\n"}, "no-table")
        self.assertEqual(self.schema_gate().returncode, 0)  # 테이블 절 없는 계약·README 템플릿은 걸지 않는다

        self.git("reset", "-q", "--hard", "origin/main")
        self.write_commit({"docs/contracts/memo.md": None}, "delete")
        self.assertEqual(self.schema_gate().returncode, 1)  # 테이블 초안이 든 계약을 지워도 사람이 본다

        self.git("reset", "-q", "--hard", "origin/main")
        self.write_commit({"docs/contracts/note.md": table.replace("memos", "notes")}, "new-contract")
        r = self.schema_gate()  # 플랜 티켓의 일반 경우: 새 계약 파일 — origin/main에 없어도 잡는다 (리허설에서 pipefail로 놓쳤던 것)
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("docs/contracts/note.md", r.stderr)

        self.git("reset", "-q", "--hard", "origin/main")
        self.write_commit({"docs/contracts/todo.md": "# todo\n\n## 테이블 (SQL 초안)\n    CREATE TABLE todos (id int);\n"}, "add-table")
        self.assertEqual(self.schema_gate().returncode, 1)  # 새로 넣어도

    def lib(self, script, **env):
        return run(["bash", "-c", f". scripts/lib.sh; {script}"], env={**self.env, "CI_POLL_SEC": "0", "CI_WAIT_MAX": "3", **env}, cwd=self.repo)

    def test_ci_wait_passes_fails_or_times_out(self):
        """ship 8단계: CI를 잠금 밖에서 기다린다 — 통과 0, 실패 1, 시간 초과 2, CI 없음 0."""
        checks = lambda *buckets: [{"name": f"c{i}", "bucket": b} for i, b in enumerate(buckets)]
        self.put("checks_pending", checks("pass", "pending"))
        self.put("checks_pass", checks("pass", "skipping"))
        self.put("checks_fail", checks("pass", "fail"))
        self.put("checks_none", [])
        (self.fix / "seq").write_text("checks_pending\nchecks_pending\nchecks_pending\nchecks_pass\n")
        r = self.lib("ci_wait 7; echo rc=$?")
        self.assertIn("CI 통과 (pass,skipping)", r.stdout)
        self.assertIn("rc=0", r.stdout)
        (self.fix / "seq").write_text("checks_pending\nchecks_pending\nchecks_fail\n")
        self.assertIn("rc=1", self.lib("ci_wait 7; echo rc=$?").stdout)
        (self.fix / "seq").write_text("checks_none\n")
        r = self.lib("ci_wait 7; echo rc=$?")
        self.assertIn("CI가 없어", r.stdout)
        self.assertIn("rc=0", r.stdout)
        (self.fix / "seq").unlink()
        self.put("pr_checks", checks("pending"))  # seq 없음 → 계속 pending
        self.assertIn("rc=2", self.lib("ci_wait 7; echo rc=$?").stdout)  # CI_WAIT_MAX=3 번 뒤 시간 초과
        # 같은 실행의 두 번째 호출(main 재반영 후 push 직후): 체크가 아직 0이어도 'CI 없음'이 아니라 생길 때까지 기다린다
        # gh 호출마다 seq 한 줄: 1차 [개수, 상태] → 2차 [개수=0, 생길 때까지 2번, 상태]
        (self.fix / "seq").write_text("checks_pass\nchecks_pass\nchecks_none\nchecks_none\nchecks_pass\nchecks_pass\n")
        r = self.lib("ci_wait 7 && ci_wait 7; echo rc=$?", CI_APPEAR_MAX="3")
        self.assertEqual(r.stdout.count("CI 통과"), 2, r.stdout)
        self.assertNotIn("CI가 없어", r.stdout)
        (self.fix / "seq").write_text("checks_pass\nchecks_pass\n")
        self.put("pr_checks", [])  # 끝내 안 생기면 2
        r = self.lib("ci_wait 7; ci_wait 7; echo rc=$?", CI_APPEAR_MAX="2")
        self.assertIn("체크가 생기지 않음", r.stdout)
        self.assertIn("rc=2", r.stdout)
        (self.fix / "seq").write_text("")  # 조회 자체가 실패하면(픽스처 없음 → gh 종료 1) 'CI 없음'이 아니라 판정 실패
        (self.fix / "pr_checks.json").unlink()
        r = self.lib("ci_wait 7; echo rc=$?", CI_APPEAR_MAX="1")
        self.assertIn("조회 실패", r.stdout)
        self.assertIn("rc=2", r.stdout)
        (self.fix / "pr_checks.nochecks").write_text("")  # gh 판에 따라 체크 0개를 오류로 내는 경우 → CI 없음
        self.assertIn("CI가 없어", self.lib("ci_wait 7; echo rc=$?").stdout)
        (self.fix / "pr_checks.nochecks").unlink()
        self.put("pr_checks", [])  # 워크플로가 있는 레포(CI_SEEN 미리 설정)에서 체크가 끝내 없으면 2, SHIP_NO_CI=1이면 통과
        r = self.lib("CI_SEEN=1 ci_wait 7; echo rc=$?", CI_APPEAR_MAX="1")
        self.assertIn("rc=2", r.stdout)
        self.assertIn("rc=0", self.lib("ci_wait 7; echo rc=$?", SHIP_NO_CI="1").stdout)
        # head SHA를 주면 PR head가 그 커밋이 될 때까지 기다린 뒤에 체크를 본다 (이전 커밋의 통과를 새 커밋 것으로 오인하지 않게)
        self.put("pr_view", {"headRefOid": "abc123"})
        self.put("pr_checks", checks("pass"))
        self.assertIn("rc=0", self.lib("ci_wait 7 abc123; echo rc=$?").stdout)
        self.put("pr_checks", checks("cancel", "cancel"))  # 모두 취소 = 통과한 체크 없음 → 실패
        self.assertIn("rc=1", self.lib("ci_wait 7; echo rc=$?").stdout)
        self.put("pr_checks", checks("pass", "cancel"))  # 대체 실행으로 취소된 것은 통과
        self.assertIn("rc=0", self.lib("ci_wait 7; echo rc=$?").stdout)
        r = self.lib("ci_wait 7 fff999; echo rc=$?", CI_APPEAR_MAX="1")
        self.assertIn("head가 push한 커밋", r.stdout)
        self.assertIn("rc=2", r.stdout)

    def test_scripts_tests_needed_only_when_scripts_changed(self):
        """verify: 키트 스크립트 자체 시험은 CI·키트 원본 레포·scripts/가 바뀐 브랜치에서만 돈다."""
        env = {k: v for k, v in self.env.items() if k != "CI"}
        self.env = env
        self.write_commit({"README.md": "x\n"}, "base")
        self.git("push", "-q", "origin", "HEAD:refs/heads/main")
        self.git("fetch", "-q", "origin")
        self.git("switch", "-q", "-c", "feat/1-x")
        self.assertEqual(self.lib("scripts_tests_needed").returncode, 1)  # 변경 없음 → 건너뜀
        self.assertEqual(self.lib("scripts_tests_needed", CI="true").returncode, 0)
        (self.repo / "scripts" / "new.sh").write_text("")  # 작업 중인 변경도 본다
        self.assertEqual(self.lib("scripts_tests_needed").returncode, 0)
        (self.repo / "scripts" / "new.sh").unlink()
        self.write_commit({"docs/x.md": "y\n"}, "docs only")
        self.assertEqual(self.lib("scripts_tests_needed").returncode, 1)
        self.write_commit({"scripts/x.sh": "echo\n"}, "script change")
        self.assertEqual(self.lib("scripts_tests_needed").returncode, 0)
        self.git("reset", "-q", "--hard", "origin/main")
        (self.repo / "templates" / "starter").mkdir(parents=True)
        (self.repo / "templates" / "starter" / "export.py").write_text("")  # 키트 원본 레포는 항상
        self.assertEqual(self.lib("scripts_tests_needed").returncode, 0)

    # ── ticket-tick.sh: 틱의 결정적인 앞부분 ──
    def tick_repo(self):
        """origin/main이 있는 main 체크아웃 + 실제로 선점 ref를 만드는 claim.sh 대역."""
        self.env.update({"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"})
        (self.repo / "scripts" / "claim.sh").write_text(
            "#!/usr/bin/env bash\nset -e\nr=$(git rev-parse --show-toplevel)\ncase \"$1\" in\n"
            "  take) t=$(git -C \"$r\" hash-object -t tree /dev/null); c=$(git -C \"$r\" commit-tree \"$t\" -m \"me #$2\" </dev/null); git -C \"$r\" push -q origin \"$c:refs/heads/claim/$2\" ;;\n"
            "  done|release) git -C \"$r\" push -q origin \":refs/heads/claim/$2\" ;;\nesac\n")
        self.write_commit({"README.md": "x\n", ".gitignore": ".run/\n"}, "base")  # 키트처럼 .run/은 무시
        self.git("branch", "-M", "main")
        self.git("push", "-q", "origin", "main")
        self.git("fetch", "-q", "origin")
        self.put("prs", [])
        self.put("pr_checks", [])

    def tick(self, **env):
        return run(["bash", str(self.repo / "scripts" / "ticket-tick.sh")], env={**self.env, **env}, cwd=self.repo)

    def test_tick_paused_or_idle(self):
        self.tick_repo()
        self.put("agent_pause", [{"number": 1}])
        r = self.tick()
        self.assertEqual((r.returncode, r.stdout.splitlines()[0]), (1, "STATE PAUSED"), r.stderr)
        self.put("agent_pause", [])
        r = self.tick()
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("STATE WAIT", r.stdout)
        self.assertIn("후보 없음", r.stdout)

    def test_tick_claims_and_prepares_branch_and_spec(self):
        """새 티켓: 선점 → 이 폴더에서 origin/main 기준 브랜치 → 본문+댓글을 spec 파일로 → 에이전트는 명세 검사부터."""
        self.tick_repo()
        self.put("issues", [issue(5, labels=["feature", "role:backend"])])
        self.put("issue_5", {"number": 5, "title": "[REQ-01][BE] 메모 API", "body": "- 선행: 없음\n완료 조건", "state": "OPEN",
                             "labels": [{"name": "feature"}, {"name": "role:backend"}]})
        self.put("issue_comments", [comment(1, "kim", "OWNER", "2026-10-02T00:00:00Z", "200자 제한")])
        r = self.tick(TICKET_ROLE="backend")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        out = dict(l.split(" ", 1) for l in r.stdout.splitlines() if " " in l)
        self.assertEqual(out["STATE"], "CLAIMED")
        self.assertTrue(out["ISSUE"].startswith("5 [REQ-01][BE]"))
        self.assertEqual(out["BRANCH"], "feat/5-req-01-be (이 폴더)")
        self.assertEqual(run(["git", "-C", str(self.repo), "branch", "--show-current"]).stdout.strip(), "feat/5-req-01-be")
        spec = Path(out["SPEC"].split()[0]).read_text()
        self.assertIn("# [REQ-01][BE] 메모 API", spec)
        self.assertIn("완료 조건", spec)
        self.assertIn("kim (2026-10-02T00:00:00Z): 200자 제한", spec)
        self.assertIn("명세 검사", out["NEXT"])
        self.assertIn("claim/5", run(["git", "-C", str(self.repo), "ls-remote", "origin", "refs/heads/claim/*"]).stdout)
        # 플랜 티켓은 docs/ 브랜치
        self.git("switch", "-q", "main")
        self.put("issues", [issue(6, labels=["plan", "role:architect"])])
        self.put("issue_6", {"number": 6, "title": "[REQ-01][plan] 계약", "body": "", "state": "OPEN", "labels": [{"name": "plan"}, {"name": "role:architect"}]})
        r = self.tick(TICKET_ROLE="architect")
        self.assertIn("BRANCH docs/6-req-01-plan (이 폴더)", r.stdout, r.stdout + r.stderr)

    def test_tick_continues_my_ticket_with_open_pr(self):
        """내 진행 중 티켓: PR 브랜치로 바꾸고 새 댓글·PR 상태를 파일과 한 줄로 — 새 티켓은 잡지 않는다."""
        self.tick_repo()
        self.git("switch", "-q", "-c", "feat/5-req-01-be")
        self.write_commit({"x.txt": "1\n"}, "wip")
        self.git("switch", "-q", "main")
        self.claim_branch(5, "me")
        self.put("issues", [issue(5), issue(7)])  # 7은 후보지만 진행 중이 있어 잡지 않는다
        self.put("issue_5", {"number": 5, "title": "[REQ-01][BE] 메모 API", "body": "", "state": "OPEN", "labels": [{"name": "role:backend"}]})
        self.put("issue_comments", [comment(1, "kim", "OWNER", "2026-10-02T00:00:00Z", "필드 하나 더")])
        self.put("prs", [{"number": 9, "state": "OPEN", "headRefName": "feat/5-req-01-be", "body": "Closes #5", "isDraft": False}])
        self.put("pr_checks", [{"name": "ci", "bucket": "pass"}])
        self.put("pr_view", {"commits": [{"committedDate": "2026-10-02T12:00:00Z", "messageHeadline": "feat: x"},
                                         {"committedDate": "2026-10-04T00:00:00Z", "messageHeadline": "Merge remote-tracking branch 'origin/main' into feat/5"}]})  # PR 댓글은 마지막 작업 커밋 이후만 '새 것' (sync Merge 제외)
        r = self.tick()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("STATE CONTINUE", r.stdout)
        self.assertIn("PR 9 OPEN checks=pass", r.stdout)
        self.assertIn("NEW_COMMENTS 1 ", r.stdout)
        self.assertIn("PR_COMMENTS 0 ", r.stdout)  # 2026-10-02T00:00 댓글은 마지막 작업 커밋(12:00) 전
        self.put("issue_comments", [comment(1, "kim", "OWNER", "2026-10-03T00:00:00Z", "리뷰: 이름 바꿔요")])  # 작업 커밋 뒤·sync Merge 전 → 새 것
        self.assertIn("PR_COMMENTS 1 ", self.tick().stdout)
        self.put("issue_comments", [comment(1, "kim", "OWNER", "2026-10-03T00:00:00Z", "리뷰: 이름 바꿔요"),
                                    comment(2, "me", "OWNER", "2026-10-03T01:00:00Z", "<!-- ticket-agent -->\n답: 계약대로입니다")])  # 답했으면 새 것 아님
        self.assertIn("PR_COMMENTS 0 ", self.tick().stdout)
        self.put("issue_comments", [comment(1, "kim", "OWNER", "2026-10-02T00:00:00Z", "옛 댓글")])
        self.assertIn("BRANCH feat/5-req-01-be (이 폴더)", r.stdout)
        self.assertIn("새 댓글", r.stdout)
        self.assertEqual(run(["git", "-C", str(self.repo), "branch", "--show-current"]).stdout.strip(), "feat/5-req-01-be")
        self.assertNotIn("claim/7", run(["git", "-C", str(self.repo), "ls-remote", "origin", "refs/heads/claim/*"]).stdout)
        self.assertIn("SPEC ", r.stdout)  # 열린 PR이 있어도 원 명세는 같은 파일로
        self.put("pr_checks", [{"name": "ci", "bucket": "fail"}])
        self.put("issue_comments", [])
        self.assertIn("체크 실패", self.tick().stdout)
        self.put("pr_checks", [{"name": "ci", "bucket": "pass"}, {"name": "old", "bucket": "cancel"}])  # 대체 실행으로 취소된 것은 실패가 아니다
        self.assertNotIn("체크 실패", self.tick().stdout)
        self.put("pr_checks", [{"name": "ci", "bucket": "cancel"}])  # 전부 취소 = 통과한 체크 없음
        self.assertIn("체크 실패", self.tick().stdout)
        self.put("prs", [{"number": 9, "state": "MERGED", "headRefName": "feat/5-req-01-be", "body": "Closes #5", "isDraft": False}])
        r = self.tick()
        self.assertEqual(r.returncode, 1)
        self.assertIn("머지됨", r.stdout)
        self.put("issue_comments", [comment(2, "kim", "OWNER", "2026-10-03T00:00:00Z", "하나만 더")])  # 머지 뒤 새 댓글 → 안내 댓글
        r = self.tick()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("'후속 Issue로' 안내 댓글을 남겼다", r.stdout)
        self.assertEqual(run(["git", "-C", str(self.repo), "branch", "--show-current"]).stdout.strip(), "main")  # 끝난 티켓 → main으로
        # 끝난(닫힌) 티켓 브랜치에 남아 있어도 다음 선점은 이 폴더에서
        self.git("push", "-q", "origin", ":refs/heads/claim/5")
        self.git("switch", "-q", "feat/5-req-01-be")
        self.put("issue_5", {"number": 5, "title": "[REQ-01][BE] 메모 API", "body": "", "state": "CLOSED", "labels": [{"name": "role:backend"}]})
        self.put("issues", [issue(7, labels=["role:backend"])])
        self.put("issue_7", {"number": 7, "title": "[REQ-02][BE] 다음", "body": "", "state": "OPEN", "labels": [{"name": "role:backend"}]})
        self.put("issue_comments", [])
        r = self.tick()
        self.assertIn("BRANCH feat/7-req-02-be (이 폴더)", r.stdout, r.stdout + r.stderr)
        # 놓은(release) 티켓의 브랜치에 남아 있어도 (Issue는 열림, 선점 ref 없음) 다음 선점은 이 폴더에서
        self.git("push", "-q", "origin", ":refs/heads/claim/7")
        self.put("issue_7", {"number": 7, "title": "[REQ-02][BE] 다음", "body": "", "state": "OPEN", "labels": [{"name": "role:backend"}, {"name": "needs-info"}]})
        self.put("issues", [issue(8, labels=["role:backend"])])
        self.put("issue_8", {"number": 8, "title": "[REQ-03][BE] 그다음", "body": "", "state": "OPEN", "labels": [{"name": "role:backend"}]})
        r = self.tick()
        self.assertIn("BRANCH feat/8-req-03-be (이 폴더)", r.stdout, r.stdout + r.stderr)

    def test_tick_other_branches(self):
        """NEEDS-HUMAN(선행에 # 없는 번호) · OTHER-SESSION · PR CLOSED · MERGE_WAIT · 명세 조회 실패."""
        self.tick_repo()
        self.put("issues", [issue(5, body="- 선행: 04")])
        self.put("issue_5", {"number": 5, "title": "t", "body": "- 선행: 04", "state": "OPEN", "labels": []})
        r = self.tick()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("STATE NEEDS-HUMAN", r.stdout)
        self.assertIn("'#' 없는 번호", r.stdout)
        self.assertEqual(run(["git", "-C", str(self.repo), "branch", "--show-current"]).stdout.strip(), "main")
        # 같은 계정의 다른 세션이 잡은 티켓
        self.claim_branch(5, "me")
        self.put("issue_5", {"number": 5, "title": "t", "body": "", "state": "OPEN", "labels": []})
        self.put("issue_comments", [comment(1, "me", "OWNER", "2026-10-02T00:00:00Z", "<!-- ticket-agent session=other1 -->\n작업 시작")])
        r = self.tick(TICKET_SESSION="mine1")
        self.assertEqual(r.returncode, 1)
        self.assertIn("STATE OTHER-SESSION", r.stdout)
        # 내 세션 + PR이 머지 없이 닫힘
        self.put("issue_comments", [])
        self.put("prs", [{"number": 9, "state": "CLOSED", "headRefName": "feat/5-t", "body": "Closes #5", "isDraft": False}])
        r = self.tick()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("PR 9 CLOSED", r.stdout)
        self.assertIn("release 5 blocked", r.stdout)
        # 열린 PR + 머지 조건이 안 풀림
        self.put("issue_5", {"number": 5, "title": "t", "body": "- 머지 조건: #11", "state": "OPEN", "labels": []})
        self.put("issue_11", {"number": 11, "state": "open"})
        self.put("prs", [{"number": 9, "state": "OPEN", "headRefName": "feat/5-t", "body": "Closes #5", "isDraft": False}])
        self.put("pr_checks", [{"name": "ci", "bucket": "pass"}])
        r = self.tick()
        self.assertIn("MERGE_WAIT #11 아직 열림", r.stdout, r.stdout + r.stderr)
        self.assertIn("머지 조건 대기 중", r.stdout)
        # PR 없음 + 댓글 조회 실패 → ERROR (빈 SPEC으로 needs-info 가지 않게)
        self.put("prs", [])
        (self.fix / "issue_comments.json").unlink()
        r = self.tick()
        self.assertEqual(r.returncode, 2)
        self.assertIn("STATE ERROR", r.stdout)

    def test_tick_uses_worktree_when_human_is_working_here(self):
        """사람이 이 폴더에서 작업 중(다른 브랜치·미커밋)이면 건드리지 않고 worktree."""
        self.tick_repo()
        self.git("switch", "-q", "-c", "fix/99-mine")
        self.claim_branch(99, "other")  # 사람이 /start-task로 잡은 티켓의 브랜치
        (self.repo / "README.md").write_text("고치는 중\n")  # 수정된 추적 파일 = 작업 중
        self.put("issues", [issue(5)])
        self.put("issue_5", {"number": 5, "title": "[REQ-02][FE] 화면", "body": "", "state": "OPEN", "labels": [{"name": "feature"}]})
        r = self.tick()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("BRANCH feat/5-req-02-fe (worktree ", r.stdout)
        self.assertIn(f"WORKDIR {os.path.realpath(self.tmp / 'repo-wt-5')}", r.stdout)
        self.assertEqual(run(["git", "-C", str(self.repo), "branch", "--show-current"]).stdout.strip(), "fix/99-mine")
        self.assertTrue((self.tmp / "repo-wt-5").is_dir())
        self.git("checkout", "-q", "--", "README.md")  # 사람이 정리하고 main으로 돌아와도 이미 있는 worktree를 계속 쓴다 (브랜치가 거기 체크아웃돼 있다)
        self.git("switch", "-q", "main")
        r = self.tick()
        self.assertIn("BRANCH feat/5-req-02-fe (worktree ", r.stdout, r.stdout + r.stderr)
        self.assertEqual(run(["git", "-C", str(self.repo), "branch", "--show-current"]).stdout.strip(), "main")
        self.git("switch", "-q", "fix/99-mine")
        (self.repo / "README.md").write_text("고치는 중\n")
        # 열린 PR이 origin에만 있는 브랜치면 worktree를 origin/<브랜치> 기준으로 만들고, 사람의 폴더는 건드리지 않는다
        self.git("switch", "-q", "-c", "feat/6-req-02-fe", "origin/main")
        self.write_commit({"y.txt": "1\n"}, "pr commit")
        self.git("push", "-q", "origin", "feat/6-req-02-fe")
        self.git("switch", "-q", "fix/99-mine")
        self.git("branch", "-D", "feat/6-req-02-fe")
        self.git("push", "-q", "origin", ":refs/heads/claim/5")  # 앞 티켓은 끝난 것으로
        self.claim_branch(6, "me")
        self.put("issues", [issue(6)])
        self.put("issue_6", {"number": 6, "title": "[REQ-02][FE] 화면2", "body": "", "state": "OPEN", "labels": []})
        self.put("prs", [{"number": 10, "state": "OPEN", "headRefName": "feat/6-req-02-fe", "body": "Closes #6", "isDraft": False}])
        self.put("pr_checks", [{"name": "ci", "bucket": "pass"}])
        before = run(["git", "-C", str(self.repo), "rev-parse", "fix/99-mine"]).stdout
        r = self.tick()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("BRANCH feat/6-req-02-fe (worktree ", r.stdout)
        self.assertEqual(run(["git", "-C", str(self.repo), "branch", "--show-current"]).stdout.strip(), "fix/99-mine")
        self.assertEqual(run(["git", "-C", str(self.repo), "rev-parse", "fix/99-mine"]).stdout, before)
        self.assertTrue((self.tmp / "repo-wt-6" / "y.txt").exists())
        # 깨끗한 main 체크아웃이면 origin에만 있는 PR 브랜치를 이 폴더에 --track으로 받는다
        self.git("switch", "-q", "main")
        self.git("checkout", "-q", "--", "README.md")
        run(["git", "-C", str(self.repo), "worktree", "remove", "--force", str(self.tmp / "repo-wt-6")])
        self.git("branch", "-D", "feat/6-req-02-fe")
        r = self.tick()
        self.assertIn("BRANCH feat/6-req-02-fe (이 폴더)", r.stdout, r.stdout + r.stderr)
        self.assertTrue((self.repo / "y.txt").exists())
        self.assertNotIn("DIVERGED", r.stdout)

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
