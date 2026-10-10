"""dev_log.py 시험 — 머지된 PR의 AI 리뷰 블록 → development.md 3절 행. 실행: python3 scripts/test_dev_log.py"""

import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("dev_log", Path(__file__).parent / "dev_log.py")
dl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dl)

DOC = """# Development

## 2. 타임라인
| 시각 | 한 일 | Issue·커밋 | 담당 |
|---|---|---|---|
| {{10/14 HH:MM}} | {{주제 분석}} | {{#1}} | {{이름}} |

## 3. AI 활용 기록
**AI가 한 것**과 **사람이 확인·수정한 것**을 구분한다.

| # | 작업 | AI가 한 것 | 사람이 확인한 방법 | 고친 것 (없으면 "없음") | 근거 |
|---|---|---|---|---|---|
| 1 | {{REQ-01 API 구현}} | {{초안 코드 생성}} | {{TC-01-3 실행}} | {{소유자 조건 추가}} | {{커밋 SHA}} |

## 4. 결정과 변경
| 시각 | 무엇을 바꿨나 |
|---|---|
"""

BODY = """## 변경
...
<!-- ship:start -->
## 확인 (make ship 자동 기록, `abc1234`)
- 검사 통과
<!-- ship:end -->
<!-- ai-review:start -->
## AI 리뷰
- 리뷰한 커밋: `abc1234`
- 총점: 51/60
- 판정: 머지 가능

### 이전 지적 처리
| # | 심각도 | 이전 지적 | 상태 | 메모 |
|---|---|---|---|---|
| 1 | 중간 | `--remove-label` 두 개를 한 명령으로 보내면 없는 라벨 하나가 전체를 실패시킨다 | 해결 | 라벨마다 따로 |
| 2 | 낮음 | 칸 수 부족 행에서 IndexError | 해결 | len 확인 |
| 3 | 낮음 | 테스트 없음 | 미해결 | 다음에 |

### 지적 사항
| 심각도 | 위치 | 문제 | 제안 | 이번 변경 |
|---|---|---|---|---|
| 낮음 | a.py:1 | 남은 것 | 고친다 | ✓ |
<!-- ai-review:end -->
"""


def pr(number, title, body="", merged_at="2026-10-14T10:00:00Z", issues=(), by="kim"):
    return {"number": number, "title": title, "body": body, "mergedAt": merged_at, "mergeCommit": {"oid": "beabcaa1234567"},
            "mergedBy": {"login": by}, "closingIssuesReferences": [{"number": n, "title": t} for n, t in issues],
            "url": f"https://github.com/o/r/pull/{number}"}


class ParseTest(unittest.TestCase):
    def test_parse_review_reads_score_fixed_and_open(self):
        r = dl.parse_review(BODY)
        self.assertEqual(r["score"], 51)
        self.assertEqual(r["fixed"], ["중간: `--remove-label` 두 개를 한 명령으로 보내면 없는 라벨 하나가 전체를 실패시킨다", "낮음: 칸 수 부족 행에서 IndexError"])
        self.assertEqual(r["open"], ["낮음: 남은 것"])
        self.assertEqual(dl.parse_review("블록 없음"), {"score": None, "fixed": [], "open": []})
        self.assertEqual(dl.parse_review("<!-- ai-review:start -->\n(AI 리뷰 대기)\n<!-- ai-review:end -->")["score"], None)


class NotesTest(unittest.TestCase):
    def test_human_notes_ignore_auto_blocks(self):
        body = "## 변경 내용\n- AI 검증: 타인 자료가 조회돼 소유자 조건 추가\n* AI 검증 : 두 번째\n<!-- ship:start -->\n- AI 검증: 블록 안은 무시\n<!-- ship:end -->\n" + BODY
        self.assertEqual(dl.human_notes(body), ["타인 자료가 조회돼 소유자 조건 추가", "두 번째"])
        self.assertEqual(dl.human_notes("없음"), [])


class InsertTest(unittest.TestCase):
    def test_rows_replace_placeholder_and_skip_recorded_and_record_prs(self):
        prs = [
            pr(12, "feat(memo): 메모 API (REQ-01, #2)", BODY, "2026-10-14T11:00:00Z", issues=[(2, "[REQ-01][BE] 메모 등록·목록 API")]),
            pr(11, "docs(memo): 계약", "## 변경 내용\n- 계약 초안\n- AI 검증: 422 형식이 틀려 FastAPI 기본으로 고침\n", "2026-10-14T10:00:00Z", issues=[(1, "[REQ-01][plan] 메모판 계약")]),
            pr(13, "docs(e2e): 시험 기록 abc (전체 PASS)", "", "2026-10-14T12:00:00Z"),  # make record — 적지 않는다
            pr(15, "feat(x): 검사에서 멈춘 뒤 사람이 머지", "<!-- ship:start -->\n(make ship 검사 중)\n<!-- ship:end -->", "2026-10-14T12:30:00Z"),  # 자리표시만 → 검사 통과 아님
        ]
        text, n = dl.insert_rows(DOC, prs)
        self.assertEqual(n, 3)
        self.assertNotIn("{{REQ-01 API 구현}}", text)  # 양식 행은 지워진다
        self.assertIn("{{10/14 HH:MM}}", text)  # 다른 절의 양식 행은 그대로
        _, _, rows, _ = dl.find_table(text)
        self.assertEqual([r[0] for r in rows], ["1", "2", "3"])
        self.assertEqual(rows[2][3], "ship 검사 기록 없음, AI 리뷰 없음, 머지 kim")  # 자리표시 블록만 있는 PR
        self.assertEqual(rows[0][1], "[REQ-01][plan] 메모판 계약 (#1)")  # 머지 순서 (11 → 12)
        self.assertEqual(rows[0][2], "PR #11: docs(memo): 계약 — AI 리뷰 없음")
        self.assertEqual(rows[0][3], "422 형식이 틀려 FastAPI 기본으로 고침 (ship 검사 기록 없음, AI 리뷰 없음, 머지 kim)")  # PR 본문의 'AI 검증:' 줄이 앞에, ship 블록이 없는 PR에 검사 통과를 적지 않는다
        self.assertEqual(rows[0][4], "없음")
        self.assertEqual(rows[1][3], "make ship 검사·e2e 통과, AI 리뷰 51/60 — 지적 2건 반영, 머지 kim")
        self.assertIn("중간: `--remove-label` 두 개를", rows[1][4])
        self.assertIn("<br>낮음: 칸 수 부족 행에서 IndexError", rows[1][4])
        self.assertEqual(rows[1][5], "[PR #12](https://github.com/o/r/pull/12) · `beabcaa`")
        self.assertEqual(dl.recorded_prs(text), {11, 12, 15})
        hand = text.replace("| 3 | feat(x)", "| 9 | 손으로 쓴 행 | x | y | z | #14 · `abc1234` |\n| 3 | feat(x)")  # 사람이 적은 Issue 번호·SHA는 PR로 보지 않는다
        self.assertEqual(dl.recorded_prs(hand), {11, 12, 15})
        # 다시 돌리면 같은 PR은 안 붙고 새 PR만 번호를 이어 붙는다
        text2, n2 = dl.insert_rows(text, prs + [pr(14, "fix(memo): 빈 내용", "", "2026-10-14T13:00:00Z")])
        self.assertEqual(n2, 1)
        self.assertEqual(dl.find_table(text2)[2][-1][:3], ["4", "fix(memo): 빈 내용", "PR #14 구현·리뷰 — AI 리뷰 없음"])  # Issue 없음 → 제목 되풀이 안 함
        self.assertEqual(dl.insert_rows(text2, prs)[1], 0)

    def test_missing_section_is_an_error(self):
        with self.assertRaises(SystemExit):
            dl.insert_rows("# 문서\n\n## 3. AI 활용 기록\n표 없음\n\n## 4. 결정\n", [pr(1, "x")])


if __name__ == "__main__":
    unittest.main()
