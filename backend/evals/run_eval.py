"""에이전트 평가. 질문 세트(cases.json)를 돌려 도구 사용·답변 내용을 규칙으로 채점한다.

    cd backend && .venv/bin/python -m evals.run_eval              # 설정된 LLM (API 비용 발생!)
    cd backend && .venv/bin/python -m evals.run_eval --provider mock  # 비용 없이 흐름만 확인
    옵션: --cases evals/cases.json --only calc-basic --min-pass 0.75

채점 규칙 (케이스별, 있는 것만 검사):
  expect_tools        이 도구들을 모두 호출했는가
  forbid_tools        이 도구들을 호출하지 않았는가
  expect_contains     최종 답변에 이 문자열이 모두 있는가
  expect_contains_any 최종 답변에 이 중 하나라도 있는가
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

from app.agent.loop import run_agent
from app.agent.types import Message


async def run_case(case: dict, provider) -> dict:
    history = [Message(role="user", content=case["input"])]
    called: list[str] = []
    usage: dict = {}
    error = None
    t0 = time.monotonic()
    async for ev in run_agent(history, provider=provider):
        if ev.type == "tool_call":
            called.append(ev.data["name"])
        elif ev.type == "done":
            usage = ev.data.get("usage", {})
        elif ev.type == "error":
            error = ev.data["message"]
    answer = "\n".join(m.content for m in history if m.role == "assistant" and m.content)

    fails = []
    if error:
        fails.append(f"error: {error}")
    fails += [f"도구 미호출: {t}" for t in case.get("expect_tools", []) if t not in called]
    fails += [f"금지 도구 호출: {t}" for t in case.get("forbid_tools", []) if t in called]
    fails += [f"답변에 없음: {s!r}" for s in case.get("expect_contains", []) if s not in answer]
    if (any_of := case.get("expect_contains_any")) and not any(s in answer for s in any_of):
        fails.append(f"답변에 다음 중 하나도 없음: {any_of}")
    return {
        "id": case["id"],
        "passed": not fails,
        "fails": fails,
        "tools": called,
        "seconds": round(time.monotonic() - t0, 1),
        "usage": usage,
        "answer": answer[:300],
    }


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default=str(Path(__file__).with_name("cases.json")))
    ap.add_argument("--provider", choices=["anthropic", "mock"], default=None)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--min-pass", type=float, default=1.0, help="이 비율 미만이면 종료코드 1")
    args = ap.parse_args()

    if args.provider == "mock":
        from app.agent.providers.mock import MockProvider

        provider = MockProvider()
    elif args.provider == "anthropic":
        from app.agent.providers.anthropic import AnthropicProvider

        provider = AnthropicProvider()
    else:
        from app.agent.providers import get_provider

        provider = get_provider()

    cases = json.loads(Path(args.cases).read_text())
    if args.only:
        cases = [c for c in cases if c["id"] in args.only]
    print(f"provider={provider.name} cases={len(cases)}\n")

    results = await asyncio.gather(*(run_case(c, provider) for c in cases))
    for r in results:
        mark = "✅" if r["passed"] else "❌"
        print(f"{mark} {r['id']:<28} tools={r['tools']} {r['seconds']}s {r['usage']}")
        for f in r["fails"]:
            print(f"     - {f}")
        if not r["passed"]:
            print(f"     answer: {r['answer']!r}")

    passed = sum(r["passed"] for r in results)
    rate = passed / len(results) if results else 0
    tokens = sum(
        r["usage"].get("input_tokens", 0) + r["usage"].get("output_tokens", 0) for r in results
    )
    print(f"\n{passed}/{len(results)} 통과 ({rate:.0%}), 마지막 턴 토큰 합계 {tokens}")
    return 0 if rate >= args.min_pass else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
