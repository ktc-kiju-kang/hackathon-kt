"""make ship PR 본문 갱신 시험. 실행: python3 scripts/test_pr_body.py (make verify가 실행)"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pr_body import update

BLOCK = "<!-- ship:start -->새 결과<!-- ship:end -->"


class UpdateTest(unittest.TestCase):
    def test_open_issue_gets_closes(self):
        self.assertEqual(update("x", BLOCK, "12", "Closes"), f"Closes #12\n\nx\n\n{BLOCK}")

    def test_closed_issue_gets_refs(self):
        self.assertTrue(update("x", BLOCK, "12", "Refs").startswith("Refs #12\n"))

    def test_leading_closes_becomes_refs_after_issue_closed(self):
        old = "Closes #12\n\n본문\n<!-- ship:start -->옛 결과<!-- ship:end -->"
        self.assertEqual(update(old, BLOCK, "12", "Refs"), f"Refs #12\n\n본문\n{BLOCK}")

    def test_existing_link_kept_and_block_replaced(self):
        old = "Fixes #12\n\n<!-- ship:start -->옛<!-- ship:end -->"
        self.assertEqual(update(old, BLOCK, "12", "Closes"), f"Fixes #12\n\n{BLOCK}")
        old = "Refs #12\n\nx"
        self.assertEqual(update(old, BLOCK, "12", "Refs").count("#12"), 1)

    def test_no_issue(self):
        self.assertEqual(update("x", BLOCK, "", "Closes"), f"x\n\n{BLOCK}")


if __name__ == "__main__":
    unittest.main()
