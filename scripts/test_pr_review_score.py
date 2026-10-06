import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pr_review_score as s  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
