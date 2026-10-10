"""readme_summary.py 시험 — README '결과 한눈에'·compliance 요약을 문서 표에서 센다. 실행: python3 scripts/test_readme_summary.py"""

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("readme_summary", HERE / "readme_summary.py")
rs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rs)

PRD = """## 요구사항
| ID | 출처 | 요구사항 | 우선순위 | Issue | 확인 조건 | 상태 |
|---|---|---|---|---|---|---|
| [REQ-01](prd/REQ-01-a.md) | 주최 (SRC-01) | a | 필수 | #1 | AC-01-1 | 검증됨 |
| **[REQ-02](prd/REQ-02-b.md)** | 주최 (SRC-02) | b | 필수 | #2 | AC-02-1 | 구현됨-미검증 |
| [REQ-11](prd/REQ-11-c.md) | 팀 | c | 선택 | - | AC-11-1 | 계획 |

## 비기능 요구
| ID | 출처 | 항목 | 기준 | 확인 |
|---|---|---|---|---|
| REQ-N1 | 주최 정책 | 보안 | SEC | TC |
"""
E2E = """## 3. 결과 요약
| 상태 | 개수 |
|---|---|
| PASS | {{n}} |

## 4. 시험 목록
| TC | 확인 조건 | 종류 | 방식 | 상태 | 근거 |
|---|---|---|---|---|---|
| TC-01-1 | AC-01-1 | 정상 | 자동 | PASS | [x](x) |
| TC-02-1 | AC-02-1 | 정상 | 자동 | FAIL | - |
| TC-02-2 | AC-02-1 | 오류 | 수동 | 미실행 | - |
| TC-S01-1 | SEC-01 | 보안 | 자동 | SKIP(정책 없음) | - |
"""
COMP = """## 1. 요약
| 상태 | 개수 |
|---|---|
| 적용-검증됨 | {{n}} |
| 적용-미검증 | {{n}} |
| 해당 없음 | {{n}} |
| 예외 | {{n}} |

## 2. 항목별 적용
| SEC | 항목 (정책 원문 이름) | 상태 | 적용 이유 / 해당 없음 이유 | 코드 위치 | 시험 | 결과 |
|---|---|---|---|---|---|---|
| SEC-01 | 입력 검증 | 적용-검증됨 | … | a.py | TC-S01-1 | PASS |
| SEC-02 | 인증 | 해당 없음(로그인 없음) | … | - | - | - |
| SEC-03 | 로그 | 적용-미검증 | … | b.py | - | - |
"""
README = """# 서비스

## 결과 한눈에
| 항목 | 값 | 근거 |
|---|---|---|
| 요구사항 | 검증됨 {{n}} / 전체 {{n}} (주최 {{n}} · 팀 {{n}}) | [prd.md](docs/prd.md) |
| 시험 | PASS {{n}} · FAIL {{n}} · SKIP {{n}} · 미실행 {{n}} | [e2e-test.md](docs/e2e-test.md) |
| 보안 | 적용-검증됨 {{n}} · 적용-미검증 {{n}} · 해당 없음 {{n}} · 예외 {{n}} | [security-compliance.md](docs/security-compliance.md) |
| 완료 Issue | {{n}} / {{n}} | {{Issues 링크}} |

## 문서
| 문서 | 내용 |
|---|---|
| [prd.md](docs/prd.md) | 요구사항 |
"""


class CountTest(unittest.TestCase):
    def test_counts_from_tables(self):
        self.assertEqual(rs.count_reqs(PRD), {"verified": 1, "total": 3, "host": 2, "team": 1})  # 비기능 표(REQ-N1)는 세지 않는다
        self.assertEqual(rs.count_tcs(E2E), {"PASS": 1, "FAIL": 1, "SKIP": 1, "미실행": 1})
        self.assertEqual(rs.count_secs(COMP), {"적용-검증됨": 1, "적용-미검증": 1, "해당 없음": 1, "예외": 0})


class FillTest(unittest.TestCase):
    def test_fill_readme_and_summary(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "docs").mkdir()
            (root / "docs/prd.md").write_text(PRD, encoding="utf-8")
            (root / "docs/e2e-test.md").write_text(E2E, encoding="utf-8")
            (root / "docs/security-compliance.md").write_text(COMP, encoding="utf-8")
            v = rs.values(root, (4, 6, "https://github.com/o/r/issues"))
            self.assertEqual(v["요구사항"], "검증됨 1 / 전체 3 (주최 2 · 팀 1)")
            self.assertEqual(v["시험"], "PASS 1 · FAIL 1 · SKIP 1 · 미실행 1")
            self.assertEqual(v["보안"], "적용-검증됨 1 · 적용-미검증 1 · 해당 없음 1 · 예외 0")
            self.assertEqual(v["완료 Issue"], "4 / 6")
            text, changed = rs.fill_readme(README, v, "https://github.com/o/r/issues")
            self.assertEqual(len(changed), 4)
            self.assertIn("| 요구사항 | 검증됨 1 / 전체 3 (주최 2 · 팀 1) | [prd.md](docs/prd.md) |", text)
            self.assertIn("| 완료 Issue | 4 / 6 | [Issues](https://github.com/o/r/issues) |", text)
            self.assertIn("| [prd.md](docs/prd.md) | 요구사항 |", text)  # 다른 표는 그대로
            self.assertEqual(rs.fill_readme(text, v)[1], [])  # 다시 돌리면 변화 없음
            comp, changed = rs.fill_compliance_summary(COMP, rs.count_secs(COMP))
            self.assertEqual(len(changed), 4)
            self.assertIn("| 적용-검증됨 | 1 |\n| 적용-미검증 | 1 |\n| 해당 없음 | 1 |\n| 예외 | 0 |", comp)
            self.assertIn("| SEC-01 | 입력 검증 | 적용-검증됨 |", comp)  # 2절은 그대로
            # gh 없이도(완료 Issue 생략) 나머지는 채운다
            v2 = rs.values(root, None)
            self.assertNotIn("완료 Issue", v2)
            self.assertIn("{{n}} / {{n}}", rs.fill_readme(README, v2)[0])


class CheckDocsTest(unittest.TestCase):
    def test_check_docs_flags_stale_readme_numbers(self):
        """README 숫자가 문서와 다르면 check-docs가 잡는다 (--draft 경고, strict 오류)."""
        # 양식(templates/submission)은 내보낸 키트에 없다 — 문서 8개를 상수로 임시 루트에 쓴다
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "docs").mkdir()
            for rel in ("docs/project-brief.md", "docs/arch.md", "docs/experience.md", "docs/development.md"):
                (root / rel).write_text("# 문서\n", encoding="utf-8")
            (root / "docs/prd.md").write_text(PRD, encoding="utf-8")
            (root / "docs/prd").mkdir()
            for rel in ("docs/prd/REQ-01-a.md", "docs/prd/REQ-02-b.md", "docs/prd/REQ-11-c.md"):
                (root / rel).write_text("# x\n", encoding="utf-8")
            (root / "docs/e2e-test.md").write_text(E2E, encoding="utf-8")
            (root / "docs/security-compliance.md").write_text(COMP, encoding="utf-8")
            (root / "README.md").write_text(README.replace("검증됨 {{n}} / 전체 {{n}} (주최 {{n}} · 팀 {{n}})", "검증됨 3 / 전체 3 (주최 2 · 팀 1)"), encoding="utf-8")
            r = subprocess.run([sys.executable, str(HERE / "check-docs.py"), "--draft", str(root)], capture_output=True, text=True)
            self.assertIn("경고  README.md: 결과 한눈에 '요구사항' 칸이 문서와 다름 (검증됨 3 / 전체 3 (주최 2 · 팀 1) → 검증됨 1 / 전체 3 (주최 2 · 팀 1))", r.stdout)
            r = subprocess.run([sys.executable, str(HERE / "check-docs.py"), str(root)], capture_output=True, text=True)
            self.assertIn("오류  README.md: 결과 한눈에 '요구사항' 칸이 문서와 다름", r.stdout)
            self.assertEqual(r.returncode, 1)
            # 자리표시({{n}})는 어긋남이 아니라 '채우지 않음'으로만 센다
            (root / "README.md").write_text(README, encoding="utf-8")
            r = subprocess.run([sys.executable, str(HERE / "check-docs.py"), "--draft", str(root)], capture_output=True, text=True)
            self.assertNotIn("결과 한눈에", r.stdout)


if __name__ == "__main__":
    unittest.main()
