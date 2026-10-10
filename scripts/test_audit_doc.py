"""audit_doc.py 시험 — make audit 결과를 security-compliance.md 4절에 적는다. 실행: python3 scripts/test_audit_doc.py"""

import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("audit_doc", Path(__file__).parent / "audit_doc.py")
ad = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ad)

DOC = """## 3. 항목별 상세
| 점검 | 방법 | 결과 |
|---|---|---|
| 다른 표 | x | y |

## 4. 공통 점검
| 점검 | 방법 | 결과 |
|---|---|---|
| 비밀값이 저장소에 없음 | {{gitleaks / grep 명령}} | {{미실행}} |
| 의존성 취약점 | {{npm audit / pip-audit}} | {{미실행}} |
| 실제 개인정보 미사용 | {{합성 데이터만 사용 — 위치}} | {{…}} |
"""


class UpdateTest(unittest.TestCase):
    def test_fills_two_rows_and_keeps_others(self):
        text, n = ad.update(DOC, "PASS — gitleaks detect 발견 0건", "npm audit(운영) FAIL — high 7·critical 0 (전체 7) · pip-audit PASS — 발견 0건", "2026-10-14 10:00 KST, abc1234")
        self.assertEqual(n, 2)
        self.assertIn("| 비밀값이 저장소에 없음 | `make audit` — gitleaks detect (push 전 `make ship`·CI Security도 검사) | PASS — gitleaks detect 발견 0건 (2026-10-14 10:00 KST, abc1234) |", text)
        self.assertIn("| 의존성 취약점 | `make audit` — frontend `npm audit --omit=dev`, backend `pip-audit` | npm audit(운영) FAIL — high 7·critical 0 (전체 7) · pip-audit PASS — 발견 0건 (2026-10-14 10:00 KST, abc1234) |", text)
        self.assertIn("| 실제 개인정보 미사용 | {{합성 데이터만 사용 — 위치}} | {{…}} |", text)  # 사람 칸은 그대로
        self.assertIn("| 다른 표 | x | y |", text)  # 같은 머리글의 표를 전부 훑되 행 이름이 맞는 곳만 바꾼다
        self.assertEqual(ad.update(text, "PASS — gitleaks detect 발견 0건", "npm audit(운영) FAIL — high 7·critical 0 (전체 7) · pip-audit PASS — 발견 0건", "2026-10-14 10:00 KST, abc1234")[1], 0)
        self.assertEqual(ad.update("표 없음\n", "a", "b", "c"), ("표 없음\n", 0))
        # 결과가 바뀌면 그 행만 다시 쓴다 (시각·SHA가 같을 때 — 다르면 두 행 다 바뀐다)
        text2, n2 = ad.update(text, "PASS — gitleaks detect 발견 0건", "npm audit(운영) PASS — high·critical 0 (전체 0) · pip-audit PASS — 발견 0건", "2026-10-14 10:00 KST, abc1234")
        self.assertEqual(n2, 1)
        self.assertIn("npm audit(운영) PASS — high·critical 0 (전체 0) · pip-audit PASS — 발견 0건 (2026-10-14 10:00 KST, abc1234)", text2)
        self.assertEqual(ad.update(text2, "PASS — gitleaks detect 발견 0건", "npm audit(운영) PASS — high·critical 0 (전체 0) · pip-audit PASS — 발견 0건", "2026-10-14 12:00 KST, def5678")[1], 2)

    def test_main_without_doc_skips(self):
        import subprocess, sys, tempfile
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run([sys.executable, str(Path(__file__).parent / "audit_doc.py"), "--secrets", "a", "--deps", "b", "--doc", f"{d}/none.md"], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0)
            self.assertIn("없음", r.stdout)
            doc = Path(d) / "c.md"; doc.write_text(DOC, encoding="utf-8")
            r = subprocess.run([sys.executable, str(Path(__file__).parent / "audit_doc.py"), "--secrets", "a", "--deps", "b", "--stamp", "s", "--doc", str(doc)], capture_output=True, text=True)
            self.assertIn("2행 갱신", r.stdout)
            self.assertIn("| 비밀값이 저장소에 없음 | `make audit`", doc.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
