"""ai-review.py 시험 — 재리뷰 수렴 규칙(이전 지적 해결 판정·이번 변경의 새 높음만 차단)과 블록 왕복. 실행: python3 scripts/test_ai_review.py"""

import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("ai_review", Path(__file__).parent / "ai-review.py")
ar = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ar)

SCORES = {"correctness": 13, "security": 9, "contract": 9, "design": 9, "tests": 8, "ops": 4}  # 52


def result(findings=(), blocking=(), previous=(), scores=SCORES):
    return {
        "scores": dict(scores), "blocking": list(blocking), "summary": "요약", "design": "설계", "risks": "위험",
        "tests": "시험", "unverified": "없음", "findings": list(findings), "previous": list(previous),
    }


def finding(severity, problem, in_delta=True, location="a.py:1"):
    return {"severity": severity, "location": location, "problem": problem, "suggestion": "고친다", "in_delta": in_delta}


class RoundTripTest(unittest.TestCase):
    def test_previous_findings_reads_rendered_block(self):
        block, total, blocking, verdict = ar.render(result([finding("높음", "A|B 문제"), finding("낮음", "사소")]), "abc123def456")
        self.assertEqual((total, blocking, verdict), (52, 0, "머지 가능"))
        commit, prev = ar.previous_findings("본문\n\n" + block)
        self.assertEqual(commit, "abc123def456")
        self.assertEqual([(p["severity"], p["problem"]) for p in prev], [("높음", "A/B 문제"), ("낮음", "사소")])
        self.assertEqual(ar.previous_findings("블록 없음"), ("", []))
        block, *_ = ar.render(result(), "abc123def456")  # 지적 없음 → 빈 목록
        self.assertEqual(ar.previous_findings(block)[1], [])
        self.assertNotIn("이전 지적 처리", block)

    def test_render_shows_previous_section_and_delta_column(self):
        prev = [{"severity": "높음", "location": "a.py", "problem": "옛 문제"}]
        r = result([finding("중간", "새 것", in_delta=False)], previous=[{"index": 1, "status": "해결", "note": "고쳐짐"}])
        block, *_ = ar.render(r, "abc123def456", prev)
        self.assertIn("### 이전 지적 처리", block)
        self.assertIn("| 1 | 높음 | 옛 문제 | 해결 | 고쳐짐 |", block)
        self.assertIn("| 중간 | a.py:1 | 새 것 | 고친다 | - |", block)


class DecideTest(unittest.TestCase):
    def test_first_review_blocks_on_high_blocking_or_low_score(self):
        self.assertEqual(ar.decide(result(), []), (False, []))
        self.assertEqual(ar.decide(result([finding("높음", "x")]), []), (True, ["높음 1건"]))
        self.assertEqual(ar.decide(result(blocking=["비밀값"]), []), (True, ["차단 1건"]))
        low = {k: 5 for k in SCORES}  # 30
        self.assertEqual(ar.decide(result(scores=low), []), (True, ["점수 30 < 42"]))

    def test_rereview_blocks_only_unresolved_or_new_high_in_delta(self):
        prev = [{"severity": "높음", "location": "a", "problem": "옛 높음"}, {"severity": "낮음", "location": "b", "problem": "옛 낮음"}]
        resolved = [{"index": 1, "status": "해결", "note": ""}, {"index": 2, "status": "미해결", "note": "낮음은 안 막는다"}]
        # 이전 높음은 해결, 새 높음은 이번 변경 밖 → 기록만, 머지
        r = result([finding("높음", "예전부터 있던 것", in_delta=False)], previous=resolved)
        self.assertEqual(ar.decide(r, prev), (False, []))
        # 이번 변경에서 생긴 새 높음 → 막는다
        r = result([finding("높음", "이번에 생김", in_delta=True)], previous=resolved)
        self.assertEqual(ar.decide(r, prev), (True, ["이번 변경의 새 높음 1건"]))
        # 이전 높음이 미해결 → 막는다
        r = result(previous=[{"index": 1, "status": "미해결", "note": ""}, {"index": 2, "status": "해결", "note": ""}])
        self.assertEqual(ar.decide(r, prev), (True, ["이전 차단·높음 미해결 1건"]))
        # 차단은 언제나
        r = result(blocking=["데이터 손실"], previous=resolved)
        self.assertEqual(ar.decide(r, prev)[1], ["차단 1건"])
        # 범위 밖 index는 무시
        r = result(previous=[{"index": 9, "status": "미해결", "note": ""}])
        self.assertEqual(ar.decide(r, prev), (False, []))


if __name__ == "__main__":
    unittest.main()
