"""요구사항 정의서(prd.md 인덱스 + docs/prd/REQ-xx.md) 검사·기록 시험 — check-docs.py, e2e-report.py.

실행: python3 scripts/test_prd_docs.py (make verify가 실행)
"""

import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE.parent / "templates" / "submission"  # 키트 원본 레포. 팀 레포에는 없어서 건너뛴다


def load(name: str):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), HERE / f"{name}.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


report = load("e2e-report")


@unittest.skipUnless(TEMPLATE.is_dir(), "제출 문서 양식이 없는 레포")
class CheckDocsTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        shutil.copytree(TEMPLATE, self.root, dirs_exist_ok=True)
        self.prd = self.root / "docs" / "prd.md"

    def tearDown(self):
        shutil.rmtree(self.root)

    def edit(self, rel: str, old: str, new: str):
        p = self.root / rel
        text = p.read_text(encoding="utf-8")
        self.assertIn(old, text)
        p.write_text(text.replace(old, new), encoding="utf-8")

    def run_check(self) -> tuple[list[str], list[str]]:
        out = subprocess.run(
            [sys.executable, str(HERE / "check-docs.py"), "--draft", str(self.root)],
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        return [x for x in out if x.startswith("오류")], [x for x in out if x.startswith("경고")]

    def test_template_passes(self):
        errors, _ = self.run_check()
        self.assertEqual(errors, [])

    def test_linked_child_missing(self):
        (self.root / "docs/prd/REQ-02.md").unlink()
        errors, _ = self.run_check()
        self.assertIn("오류  prd.md: 링크한 docs/prd/REQ-02.md 없음", errors)

    def test_unlinked_child(self):
        shutil.copy(self.root / "docs/prd/REQ-02.md", self.root / "docs/prd/REQ-03-extra.md")
        shutil.copy(self.root / "docs/prd/REQ-02.md", self.root / "docs/prd/_draft.md")  # _는 무시
        errors, _ = self.run_check()
        self.assertEqual(
            errors, ["오류  docs/prd/REQ-03-extra.md: prd.md 요구사항 표에서 링크되지 않음"]
        )

    def test_link_points_to_other_req(self):
        self.edit("docs/prd.md", "[REQ-02](prd/REQ-02.md)", "[REQ-02](prd/REQ-11.md)")
        errors, _ = self.run_check()
        self.assertIn("오류  prd.md: REQ-02의 링크가 다른 REQ 파일을 가리킴 (prd/REQ-11.md)", errors)

    def test_bad_child_name(self):
        self.edit("docs/prd.md", "[REQ-02](prd/REQ-02.md)", "[REQ-02](prd/req2.md)")
        errors, _ = self.run_check()
        self.assertTrue(any("이름은 prd/REQ-01-<설명>.md 형식" in e for e in errors), errors)

    def test_ac_of_other_req_in_child(self):
        self.edit("docs/prd/REQ-02.md", "| AC-02-1 |", "| AC-03-1 |")
        errors, _ = self.run_check()
        self.assertIn("오류  docs/prd/REQ-02.md: AC-03-1는 REQ-02의 확인 조건이 아님", errors)

    def test_req_table_in_child(self):
        with (self.root / "docs/prd/REQ-02.md").open("a", encoding="utf-8") as f:
            f.write("\n| ID | 상태 |\n|---|---|\n| REQ-02 | 계획 |\n")
        errors, _ = self.run_check()
        self.assertIn("오류  docs/prd/REQ-02.md: REQ 표는 부모 prd.md에만 둔다 (상태가 두 곳이 됨)", errors)

    def test_ac_summary_column_mismatch(self):
        self.edit("docs/prd.md", "AC-01-1, AC-01-2, AC-01-3", "AC-01-1, AC-01-2")
        errors, _ = self.run_check()
        self.assertEqual(
            errors,
            [
                "오류  prd.md: REQ-01의 '확인 조건' 칸(AC-01-1, AC-01-2)이"
                " 정의된 AC(AC-01-1, AC-01-2, AC-01-3)와 다름"
            ],
        )

    def test_src_only_in_question_is_not_linked(self):
        self.edit("docs/prd.md", "| 주최 (SRC-02) |", "| 주최 |")
        self.edit("docs/prd.md", "{{SRC-·REQ-}}", "SRC-02")  # 질문 표에만 남은 SRC
        _, warns = self.run_check()
        self.assertIn("경고  prd.md: SRC-02가 어느 REQ의 출처나 '범위 밖'에도 없음", warns)

    def test_src_out_of_scope_is_linked(self):
        self.edit("docs/prd.md", "| 주최 (SRC-02) |", "| 주최 |")
        self.edit("docs/prd.md", "| {{SRC-}} |", "| SRC-02 |")
        _, warns = self.run_check()
        self.assertFalse(any("SRC-02" in w for w in warns), warns)

    def test_undefined_flow_warns(self):
        self.edit("docs/prd/REQ-02.md", "관련 흐름: FLOW-01", "관련 흐름: FLOW-09")
        errors, warns = self.run_check()
        self.assertEqual(errors, [])
        self.assertIn("경고  docs/prd/REQ-02.md: FLOW-09가 experience.md 흐름 표에 정의되지 않음", warns)
        self.assertFalse(any("FLOW-01" in w for w in warns), warns)

    def test_single_file_prd_still_works(self):
        """하위 문서 없이 prd.md 한 파일에 AC를 둔 예전 형식."""
        shutil.rmtree(self.root / "docs/prd")
        self.edit("docs/prd.md", "[REQ-01](prd/REQ-01.md)", "REQ-01")
        self.edit("docs/prd.md", "[REQ-02](prd/REQ-02.md)", "REQ-02")
        self.edit("docs/prd.md", "[REQ-11](prd/REQ-11.md)", "REQ-11")
        with self.prd.open("a", encoding="utf-8") as f:
            f.write(
                "\n| AC | 조건 | 종류 | 시험 |\n|---|---|---|---|\n"
                "| AC-01-1 | a | 오류 | TC-01-1 |\n| AC-01-2 | b | 정상 | TC-01-2 |\n"
                "| AC-01-3 | c | 권한 | TC-01-3 |\n| AC-02-1 | d | 정상 | TC-02-1 |\n"
                "| AC-11-1 | e | 정상 | TC-11-1 |\n"
            )
        errors, _ = self.run_check()
        self.assertEqual(errors, [])


class UpdatePrdTest(unittest.TestCase):
    PRD = (
        "| ID | 출처 | 요구사항 | 우선순위 | Issue | 확인 조건 | 상태 |\n"
        "|---|---|---|---|---|---|---|\n"
        "| **[REQ-01](prd/REQ-01-a.md)** | 주최 | a | 필수 | #1 | AC-01-1 | 계획 |\n"
        "| [REQ-02](prd/REQ-02-b.md) | 주최 | b | 필수 | #2 | AC-02-1 | 계획 |\n"
    )
    CHILDREN = (
        "| AC | 조건 | 종류 | 시험 |\n|---|---|---|---|\n| AC-01-1 | x | 정상 | TC-01-1 |\n\n"
        "| AC | 조건 | 종류 | 시험 |\n|---|---|---|---|\n| AC-02-1 | y | 정상 | TC-02-1 |\n"
    )

    def test_status_from_child_ac_written_to_index(self):
        new, changed = report.update_prd(
            self.PRD, {"TC-01-1": "PASS", "TC-02-1": "FAIL"}, self.CHILDREN
        )
        self.assertEqual(changed, ["REQ-01 계획 → 검증됨", "REQ-02 계획 → 구현됨-미검증"])
        self.assertIn("| **[REQ-01](prd/REQ-01-a.md)** |", new)  # 링크·장식은 그대로 둔다

    def test_prd_children_reads_linked_files(self):
        with tempfile.TemporaryDirectory() as d:
            docs = Path(d)
            (docs / "prd").mkdir()
            (docs / "prd/REQ-01-a.md").write_text("A", encoding="utf-8")
            (docs / "prd/REQ-09-x.md").write_text("링크 안 됨", encoding="utf-8")
            (docs / "prd.md").write_text(self.PRD, encoding="utf-8")  # REQ-02 파일은 없음
            self.assertEqual(report.prd_children(docs / "prd.md"), "A")


if __name__ == "__main__":
    unittest.main()
