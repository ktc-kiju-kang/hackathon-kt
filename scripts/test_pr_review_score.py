import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pr_review_score as s


class ClassifyTest(unittest.TestCase):
    def test_is_code(self):
        self.assertTrue(s.is_code("backend/app/services/radar.py"))
        self.assertTrue(s.is_code("frontend/src/features/radar/api.ts"))
        self.assertFalse(s.is_code("backend/tests/test_radar.py"))
        self.assertFalse(s.is_code("frontend/src/lib/sse.test.ts"))
        self.assertFalse(s.is_code("frontend/src/components/ui/button.tsx"))
        self.assertFalse(s.is_code("docs/SDLC.md"))

    def test_is_test(self):
        self.assertTrue(s.is_test("backend/tests/test_radar.py"))
        self.assertTrue(s.is_test("frontend/src/lib/sse.test.ts"))
        self.assertFalse(s.is_test("backend/app/services/radar.py"))

    def test_size_excluded(self):
        self.assertTrue(s.is_size_excluded("frontend/package-lock.json"))
        self.assertTrue(s.is_size_excluded("frontend/src/components/ui/card.tsx"))
        self.assertTrue(s.is_size_excluded("backend/data/signals/x.csv"))
        self.assertFalse(s.is_size_excluded("backend/app/main.py"))

    def test_is_contract_affecting(self):
        self.assertTrue(s.is_contract_affecting("backend/app/routers/radar.py"))
        self.assertTrue(s.is_contract_affecting("backend/app/schemas/radar.py"))
        self.assertTrue(s.is_contract_affecting("frontend/src/features/radar/api.ts"))
        self.assertFalse(s.is_contract_affecting("backend/app/services/radar.py"))


def F(path, add=0, dele=0):
    return {"filename": path, "additions": add, "deletions": dele}


class ScoreTest(unittest.TestCase):
    def test_issue(self):
        self.assertEqual(s.score_issue("docs: x", "").score, 6)  # 면제
        self.assertEqual(s.score_issue("chore(ci): x", "").score, 6)
        self.assertEqual(s.score_issue("feat(a): x", "Closes #12").score, 6)
        self.assertEqual(s.score_issue("fix: x", "fixes #3").score, 6)
        self.assertEqual(s.score_issue("feat: x", "관련 #9").score, 4)
        self.assertEqual(s.score_issue("feat: x", "없음").score, 0)

    def test_tests(self):
        self.assertEqual(s.score_tests([F("docs/a.md", 5)]).score, 8)  # 코드 변경 없음
        code, test = F("backend/app/a.py", 100), F("backend/tests/test_a.py", 10)
        self.assertEqual(s.score_tests([code, test]).score, 8)
        self.assertEqual(s.score_tests([F("backend/app/a.py", 30)]).score, 5)  # 30 이하
        self.assertEqual(s.score_tests([F("backend/app/a.py", 20, 11)]).score, 0)  # 31

    def test_contract(self):
        r, c = F("backend/app/routers/radar.py", 3), F("docs/contracts/radar.md", 3)
        self.assertEqual(s.score_contract([r]).score, 0)
        self.assertEqual(s.score_contract([r, c]).score, 5)
        self.assertEqual(s.score_contract([F("backend/app/services/radar.py")]).score, 5)

    def test_size(self):
        self.assertEqual(s.score_size([F("backend/app/a.py", 400)]).score, 4)
        self.assertEqual(s.score_size([F("backend/app/a.py", 401)]).score, 2)
        self.assertEqual(s.score_size([F("backend/app/a.py", 800)]).score, 2)
        self.assertEqual(s.score_size([F("backend/app/a.py", 801)]).score, 0)
        big = F("frontend/package-lock.json", 5000)
        self.assertEqual(s.score_size([F("backend/app/a.py", 10), big]).score, 4)  # 제외

    def test_commits(self):
        ok, bad = "feat(x): a", "수정함"
        self.assertEqual(s.score_commits([ok, ok, ok]).score, 3)
        self.assertEqual(s.score_commits([ok, ok, bad]).score, 2)  # 2/3*3=2
        self.assertEqual(s.score_commits([ok, bad, bad]).score, 1)
        self.assertEqual(s.score_commits([bad]).score, 0)
        self.assertEqual(s.score_commits(["Merge branch 'main'", ok]).score, 3)  # 머지 제외
        self.assertEqual(s.score_commits(["Merge branch 'main'"]).score, 3)  # 대상 없음

    def test_body(self):
        full = "## 변경\n" + "가" * 200 + "\n## 검증\n- npm test 통과\n"
        self.assertEqual(s.score_body(full).score, 4)
        self.assertEqual(s.score_body("짧음").score, 0)
        self.assertEqual(s.score_body("## 변경\n" + "가" * 200).score, 2)  # 길이+변경
        no_item = "## 변경\n" + "가" * 200 + "\n## 검증\n\n"
        self.assertEqual(s.score_body(no_item).score, 2)
        alt = "## 변경 내용\n" + "가" * 200 + "\n## 확인\n1. 해봄\n"
        self.assertEqual(s.score_body(alt).score, 4)


class LintTest(unittest.TestCase):
    def names(self, items):
        return {i.name: i for i in items}

    def test_not_applicable_is_full(self):
        items = s.score_lint(False, False, None, None, None, None)
        self.assertTrue(all(i.score == i.max and i.measured for i in items))
        self.assertEqual(sum(i.max for i in items), 10)

    def test_frontend_eslint(self):
        d = self.names(s.score_lint(True, False, 0, None, None, None))
        self.assertEqual(d["ESLint"].score, 3)
        d = self.names(s.score_lint(True, False, 2, None, None, None))
        self.assertEqual(d["ESLint"].score, 0)

    def test_backend(self):
        d = self.names(s.score_lint(False, True, None, 0, True, 0))
        self.assertEqual([d[k].score for k in ("ruff check", "ruff format", "ty")], [3, 2, 2])
        d = self.names(s.score_lint(False, True, None, 4, False, 1))
        self.assertEqual([d[k].score for k in ("ruff check", "ruff format", "ty")], [0, 0, 1])
        d = self.names(s.score_lint(False, True, None, 0, True, 3))
        self.assertEqual(d["ty"].score, 0)

    def test_unmeasured(self):
        d = self.names(s.score_lint(True, False, None, None, None, None))
        self.assertFalse(d["ESLint"].measured)

    def test_total_scales_over_measured(self):
        items = [s.Item("a", 6, 6), s.Item("b", 0, 4, measured=False), s.Item("c", 0, 10)]
        total, missing = s.auto_total(items)
        self.assertEqual(total, 15)  # 6/16 * 40
        self.assertEqual(missing, ["b"])
        self.assertEqual(s.auto_total([s.Item("a", 5, 5, measured=False)]), (0, ["a"]))


def block(commit="abc1234", total=52, blocking="없음", scores=None, sections=True):
    scores = scores or [13, 10, 10, 8, 7, 4]
    rows = "\n".join(f"| {n} | {v}/{m} |" for (n, m), v in zip(s.AI_ITEMS.items(), scores))
    secs = "\n".join(f"### {h}" for h in s.AI_SECTIONS) if sections else ""
    return (
        f"본문\n<!-- ai-review:start -->\n## AI 리뷰\n- 리뷰한 커밋: `{commit}`\n"
        f"- 총점: {total}/60\n- 판정: 지적 처리 후 머지\n- 차단 이슈: {blocking}\n\n"
        f"| 항목 | 점수 |\n|---|---|\n{rows}\n\n{secs}\n<!-- ai-review:end -->\n"
    )


class AiBlockTest(unittest.TestCase):
    def test_ok(self):
        r = s.parse_ai_block(block())
        self.assertEqual(r.errors, [])
        self.assertEqual((r.total, r.commit, r.blocking), (52, "abc1234", 0))

    def test_blocking_count(self):
        self.assertEqual(s.parse_ai_block(block(blocking="2건")).blocking, 2)

    def test_missing_block(self):
        r = s.parse_ai_block("블록 없음")
        self.assertTrue(r.errors)

    def test_sum_mismatch(self):
        self.assertTrue(s.parse_ai_block(block(total=50)).errors)

    def test_item_over_max(self):
        r = s.parse_ai_block(block(total=56, scores=[16, 10, 10, 8, 7, 5]))
        self.assertTrue(any("배점" in e for e in r.errors))

    def test_missing_item(self):
        text = block().replace("| 배포·운영 안전 | 4/5 |\n", "")
        self.assertTrue(s.parse_ai_block(text).errors)

    def test_bad_commit(self):
        self.assertTrue(s.parse_ai_block(block(commit="xyz")).errors)

    def test_missing_sections_are_warnings(self):
        r = s.parse_ai_block(block(sections=False))
        self.assertEqual(r.errors, [])
        self.assertEqual(len(r.warnings), len(s.AI_SECTIONS))

    def test_freshness(self):
        shas = ["aaa1111" + "0" * 33, "bbb2222" + "0" * 33, "ccc3333" + "0" * 33]
        self.assertEqual(s.commits_behind("ccc3333", shas), 0)
        self.assertEqual(s.commits_behind("aaa1111", shas), 2)
        self.assertIsNone(s.commits_behind("ddd4444", shas))

    def test_verdict(self):
        self.assertEqual(s.verdict(90, 0, True), "머지 가능")
        self.assertEqual(s.verdict(85, 0, True), "머지 가능")
        self.assertEqual(s.verdict(84, 0, True), "지적 처리 후 머지")
        self.assertEqual(s.verdict(70, 0, True), "지적 처리 후 머지")
        self.assertEqual(s.verdict(69, 0, True), "수정 필요")
        self.assertEqual(s.verdict(99, 1, True), "수정 필요")  # 차단 이슈
        self.assertEqual(s.verdict(40, 0, False), "AI 리뷰 필요")


class RenderTest(unittest.TestCase):
    def test_sanitize(self):
        out = s.sanitize("@octocat [x](http://e.com) <script>\n줄바꿈", 200)
        self.assertNotIn("@octocat", out)
        self.assertNotIn("](", out)
        self.assertNotIn("<script>", out)
        self.assertNotIn("\n", out)
        self.assertEqual(len(s.sanitize("가" * 500, 100)), 101)  # 100 + …

    def _render(self, ai=None, behind=0):
        items = [s.Item("이슈 연결", 6, 6, "Closes 있음"), s.Item("ty", 0, 2, "측정 못 함", False)]
        return s.render_comment(items, 38, ["ty"], ai, behind, "abc1234")

    def test_marker_and_no_ai(self):
        out = self._render()
        self.assertTrue(out.startswith(s.MARKER))
        self.assertIn("AI 리뷰 필요", out)
        self.assertIn("38/40", out)
        self.assertIn("측정 못 함", out)

    def test_with_ai_and_stale(self):
        ai = s.parse_ai_block(block())
        out = self._render(ai, behind=2)
        self.assertIn("90/100", out)
        self.assertIn("최신 아님", out)
        self.assertIn("2개 커밋", out)

    def test_ai_errors_listed(self):
        ai = s.parse_ai_block(block(total=50))
        out = self._render(ai)
        self.assertIn("형식 오류", out)
        self.assertIn("항목 합", out)


class LintParseTest(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())

    def test_eslint(self):
        (self.d / "eslint.json").write_text(
            json.dumps(
                [{"errorCount": 2, "warningCount": 5}, {"errorCount": 1, "warningCount": 0}]
            )
        )
        self.assertEqual(s.count_eslint(self.d), 3)
        self.assertIsNone(s.count_eslint(self.d / "nope"))

    def test_ruff(self):
        (self.d / "ruff.json").write_text(json.dumps([{"code": "E501"}, {"code": "F401"}]))
        self.assertEqual(s.count_ruff(self.d), 2)

    def test_ruff_format(self):
        (self.d / "ruff-format.code").write_text("0\n")
        self.assertTrue(s.format_ok(self.d))
        (self.d / "ruff-format.code").write_text("1\n")
        self.assertFalse(s.format_ok(self.d))

    def test_ty(self):
        (self.d / "ty.txt").write_text(
            "app/a.py:1:2: error[x] 메시지\napp/b.py:3:4: warning[y] 메시지\nFound 2 diagnostics\n"
        )
        self.assertEqual(s.count_ty(self.d), 2)
        (self.d / "ty.txt").write_text("All checks passed!\n")
        self.assertEqual(s.count_ty(self.d), 0)

    def test_broken_json_is_unmeasured(self):
        (self.d / "ruff.json").write_text("not json")
        self.assertIsNone(s.count_ruff(self.d))


if __name__ == "__main__":
    unittest.main()
