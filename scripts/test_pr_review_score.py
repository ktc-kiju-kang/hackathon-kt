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


if __name__ == "__main__":
    unittest.main()
