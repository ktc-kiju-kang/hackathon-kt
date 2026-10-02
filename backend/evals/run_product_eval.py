"""Product Generator 평가. 사업 기회 → Product Card를 생성해 규칙으로 채점한다.

    cd backend && .venv/bin/python -m evals.run_product_eval  # 설정된 LLM (실제 API 비용 발생!)
    cd backend && .venv/bin/python -m evals.run_product_eval --provider mock  # 비용 없이 흐름만
    옵션: --cases evals/product_cases.json --only product-cloudops

케이스 1개 = LLM 호출 2~3회 (요청당 상한 3회).
채점 규칙 (있는 것만 검사):
  expect_any_text  제품 이름·문제·기능에 이 중 하나가 있는가
  max_weeks        PoC 기간이 이 주 이하인가 (notes 요구 반영 확인)
  (항상) 오류 없이 done으로 끝나고, 근거가 서버 값으로 채워졌는가
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
from app.schemas.product import ProductRequest
from app.services import product


async def run_case(case: dict) -> dict:
    events: list[tuple[str, dict]] = []

    async def emit(event: str, data: dict) -> None:
        events.append((event, data))

    req = ProductRequest(opportunity=case["opportunity"], notes=case.get("notes"))
    t0 = time.monotonic()
    fails = []
    try:
        budget = CallBudget(product.MAX_CALLS)
        await product._run(req, StageRunner(emit, budget, get_provider(), product.SYSTEM))
    except Exception as e:  # StructuredError 등
        fails.append(f"error: {getattr(e, 'code', type(e).__name__)} {e}")
    card = next((d["product"] for e, d in events if e == "product"), None)
    if not fails and events[-1][0] != "done":
        fails.append(f"마지막 이벤트가 done이 아님: {events[-1][0]}")
    if card:
        text = " ".join([card["name"], card["problem"]] + [f["name"] for f in card["features"]])
        any_of = case.get("expect_any_text")
        if any_of and not any(s in text for s in any_of):
            fails.append(f"제품에 다음 중 하나도 없음: {any_of}")
        weeks = card["poc_plan"]["duration_weeks"]
        if (limit := case.get("max_weeks")) and weeks > limit:
            fails.append(f"PoC {weeks}주 > {limit}주")
        if not card["evidence"] or not card["evidence"][0]["label"]:
            fails.append("근거가 채워지지 않음")
    elif not fails:
        fails.append("product 이벤트 없음")
    return {
        "id": case["id"],
        "passed": not fails,
        "fails": fails,
        "name": card["name"] if card else None,
        "seconds": round(time.monotonic() - t0, 1),
    }


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default=str(Path(__file__).parent / "product_cases.json"))
    ap.add_argument("--only")
    ap.add_argument("--provider", help="mock 이면 LLM 없이 흐름만")
    args = ap.parse_args()
    if args.provider:
        from app.core.config import settings

        settings.llm_provider = args.provider
        get_provider.cache_clear()

    cases = json.loads(Path(args.cases).read_text("utf-8"))
    if args.only:
        cases = [c for c in cases if c["id"] == args.only]
    results = [await run_case(c) for c in cases]
    for r in results:
        print(f"[{'PASS' if r['passed'] else 'FAIL'}] {r['id']} ({r['seconds']}s) {r['name']}")
        for f in r["fails"]:
            print(f"    - {f}")
    passed = sum(r["passed"] for r in results)
    print(f"\n{passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
