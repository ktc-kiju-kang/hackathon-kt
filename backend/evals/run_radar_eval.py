"""Opportunity Radar 평가. 그룹사별로 기회를 생성해 규칙으로 채점한다.

    cd backend && .venv/bin/python -m evals.run_radar_eval  # 설정된 LLM (실제 API 비용 발생!)
    cd backend && .venv/bin/python -m evals.run_radar_eval --provider mock  # 비용 없이 흐름만 확인
    옵션: --cases evals/radar_cases.json --only radar-kt-cloud-ops

케이스 1개 = LLM 호출 3회 이상 (Gemini 무료 등급은 하루 20회 한도에 주의).
채점 규칙 (있는 것만 검사):
  expect_any_opportunity_matches  기회 하나 이상의 제목·문제·해결에 이 중 하나가 있는가
  forbid_opportunity_matches      어떤 기회에도 이 문구가 없는가
  (항상) 오류 없이 done으로 끝나고, 모든 기회에 근거(evidence)가 1개 이상 있는가
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

from app.agent.providers import get_provider
from app.agent.stages import StageRunner
from app.agent.structured import CallBudget
from app.schemas.radar import OpportunityRequest
from app.services import radar


async def run_case(case: dict) -> dict:
    events: list[tuple[str, dict]] = []

    async def emit(event: str, data: dict) -> None:
        events.append((event, data))

    req = OpportunityRequest(company_id=case["company_id"], count=case.get("count", 4))
    company = radar.get_company(req.company_id)
    t0 = time.monotonic()
    fails = []
    try:
        runner = StageRunner(emit, CallBudget(), get_provider(), radar.SYSTEM)
        await radar._run(req, company, runner)
    except Exception as e:  # StructuredError 등
        fails.append(f"error: {getattr(e, 'code', type(e).__name__)} {e}")
    opps = [d["opportunity"] for e, d in events if e == "opportunity"]
    text = "\n".join(f"{o['title']} {o['problem']} {o['solution']}" for o in opps)

    if not fails and events[-1][0] != "done":
        fails.append(f"마지막 이벤트가 done이 아님: {events[-1][0]}")
    fails += [f"근거 없음: {o['title']}" for o in opps if not o["evidence"]]
    any_of = case.get("expect_any_opportunity_matches")
    if any_of and not any(s in text for s in any_of):
        fails.append(f"기회에 다음 중 하나도 없음: {any_of}")
    fails += [f"금지 문구: {s!r}" for s in case.get("forbid_opportunity_matches", []) if s in text]
    return {
        "id": case["id"],
        "passed": not fails,
        "fails": fails,
        "titles": [o["title"] for o in opps],
        "seconds": round(time.monotonic() - t0, 1),
    }


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default=str(Path(__file__).parent / "radar_cases.json"))
    ap.add_argument("--only")
    ap.add_argument("--provider", help="mock 이면 LLM 없이 흐름만")
    args = ap.parse_args()
    if args.provider:
        from app.config import settings

        settings.llm_provider = args.provider
        get_provider.cache_clear()

    cases = json.loads(Path(args.cases).read_text("utf-8"))
    if args.only:
        cases = [c for c in cases if c["id"] == args.only]
    results = [await run_case(c) for c in cases]  # 순서대로 (무료 등급 분당 한도)
    for r in results:
        mark = "PASS" if r["passed"] else "FAIL"
        print(f"[{mark}] {r['id']} ({r['seconds']}s) {r['titles']}")
        for f in r["fails"]:
            print(f"    - {f}")
    passed = sum(r["passed"] for r in results)
    print(f"\n{passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
