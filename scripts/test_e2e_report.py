"""e2e-report.py 시험 — 문서의 시험 파일과 다른 테스트(키트 샘플 등)는 TC로 집계하지 않는다. 실행: python3 scripts/test_e2e_report.py"""

import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("e2e_report", Path(__file__).parent / "e2e-report.py")
er = importlib.util.module_from_spec(spec)
spec.loader.exec_module(er)

DOC = """## 4. 시험 목록
| TC | 확인 조건 | 종류 | 방식 | 상태 | 근거 |
|---|---|---|---|---|---|
| TC-01-1 | AC-01-1 | 정상 | 자동: e2e/test_memo.py | 미실행 | - |
| TC-01-2 | AC-01-2 | 경계 | `자동: backend/tests/test_memo.py` | 미실행 | - |
| TC-01-7 | AC-01-7 | 정상 | 수동 (브라우저 캡처) | 미실행 | - |
| TC-01-8 | AC-01-8 | 정상 | 화면: frontend/src/features/memo/memo.test.ts | 미실행 | - |
| TC-02-1 | AC-02-1 | 정상 | {{자동: tests/…}} | 미실행 | - |
"""


def case(cls, name, status="PASS"):
    return {"name": name, "cls": cls, "status": status, "why": "", "suite": "x.xml"}


class DocFilesTest(unittest.TestCase):
    def test_reads_test_files_from_method_column(self):
        files = er.doc_test_files(DOC)
        self.assertEqual(files["TC-01-1"], ["e2e/test_memo.py"])
        self.assertEqual(files["TC-01-2"], ["backend/tests/test_memo.py"])
        self.assertEqual(files["TC-01-7"], [])  # 수동 → 제한 없음
        self.assertEqual(files["TC-01-8"], ["frontend/src/features/memo/memo.test.ts"])
        self.assertEqual(files["TC-02-1"], [])  # 양식 자리표시 → 제한 없음

    def test_file_matches_pytest_and_vitest_classnames(self):
        self.assertTrue(er.file_matches("e2e.test_memo", ["e2e/test_memo.py"]))
        self.assertTrue(er.file_matches("tests.test_memo", ["backend/tests/test_memo.py"]))
        self.assertTrue(er.file_matches("tests.test_memo.TestList", ["backend/tests/test_memo.py"]))  # 클래스 안의 테스트
        self.assertTrue(er.file_matches("src/features/memo/memo.test.ts", ["frontend/src/features/memo/memo.test.ts"]))
        self.assertFalse(er.file_matches("tests.test_dashboard", ["e2e/test_memo.py"]))  # 키트 샘플 테스트
        self.assertFalse(er.file_matches("tests.test_memo_extra", ["backend/tests/test_memo.py"]))  # 접두만 같은 다른 파일


class AggregateTest(unittest.TestCase):
    def test_sample_tests_with_same_tc_id_do_not_count(self):
        """리허설: BE가 없는 FE PR에서 키트 샘플(test_dashboard.py의 TC-01-1)이 팀 TC-01-1을 PASS로 만들었다."""
        cases = [
            case("tests.test_dashboard", "test_tc_01_1_pr_age"),  # 키트 샘플 — 팀 TC-01-1이 아니다
            case("e2e.test_memo", "test_tc_01_1_create"),
            case("tests.test_memo", "test_tc_01_2_exactly_200", "FAIL"),
            case("src/features/memo/memo.test.ts", "TC-01-8 목록은 새것부터"),
            case("tests.test_other", "test_tc_02_1_whatever"),  # 문서가 파일을 안 적었으면 그대로 센다
        ]
        results = er.aggregate(cases, er.doc_test_files(DOC))
        self.assertEqual({k: v["status"] for k, v in results.items()}, {"TC-01-1": "PASS", "TC-01-2": "FAIL", "TC-01-8": "PASS", "TC-02-1": "PASS"})
        self.assertEqual([c["name"] for c in results["TC-01-1"]["tests"]], ["test_tc_01_1_create"])
        self.assertEqual(cases[0].get("ignored"), "TC-01-1")
        # 문서가 없으면(키트 원본 레포) 예전처럼 전부 센다
        self.assertEqual(len(er.aggregate([case("tests.test_dashboard", "test_tc_01_1_x")])["TC-01-1"]["tests"]), 1)


if __name__ == "__main__":
    unittest.main()
