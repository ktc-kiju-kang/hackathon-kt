"""데모 스냅샷 생성: 실제 LLM으로 radar → 기회마다 product를 만들어
`data/demo/<company_id>.json`에 저장한다.

    cd backend && .venv/bin/python -m evals.make_demo_snapshot --company kt-cloud  # 실제 API 호출!
    옵션: --count 3 (기회 수, 3~5) · --provider mock (흐름만, 저장 안 함 — 테스트용)

LLM 호출 수 ≈ radar 3 + product 2 × count. 결과는 공개 저장소에 커밋되므로 공개 데이터로만 만든다.
"""

import argparse
import asyncio
import sys
from datetime import UTC, datetime

from app.agent.providers import LLMProvider, get_provider
from app.agent.stages import StageRunner
from app.agent.structured import CallBudget, StructuredError
from app.schemas.product import ProductCard, ProductRequest
from app.schemas.radar import Opportunity, OpportunityRequest, SnapshotInfo
from app.services import product, radar, snapshot

PAUSE = 20.0  # 단계 사이 쉬는 시간 (Groq 무료 분당 8,000토큰)
RATE_WAIT = 65.0  # 한도에 걸리면 1분 넘게 기다렸다 그 단계만 다시
RATE_RETRIES = 2


async def _patient(make, provider: LLMProvider):
    """연속 생성용 (서버 재시도는 최대 20초라 부족): 한도·일시 오류면 길게 기다렸다 다시 한다."""
    for attempt in range(RATE_RETRIES + 1):
        try:
            return await make()
        except StructuredError as e:
            if provider.name == "mock" or e.code not in ("rate_limit", "unavailable"):
                raise
            if attempt == RATE_RETRIES:
                raise
            print(f"  한도·일시 오류({e.code}) → {RATE_WAIT:.0f}초 뒤 다시")
            await asyncio.sleep(RATE_WAIT)


async def build(company_id: str, count: int, provider: LLMProvider) -> snapshot.SnapshotFile:
    """radar 1회 + 기회마다 product 1회. 실패하면 StructuredError를 그대로 던진다."""
    events: list[tuple[str, dict]] = []

    async def emit(event: str, data: dict) -> None:
        events.append((event, data))
        if event == "retry":
            print(f"  재시도 대기 {data['wait_seconds']}초 ({data['code']})")

    req = OpportunityRequest(company_id=company_id, count=count)
    company = radar.get_company(company_id)
    print(f"radar: {company.name}")

    async def make_radar():
        events.clear()
        runner = StageRunner(emit, CallBudget(), provider, radar.SYSTEM)
        await radar._run(req, company, runner)

    await _patient(make_radar, provider)
    opps = [Opportunity.model_validate(d["opportunity"]) for e, d in events if e == "opportunity"]

    products: dict[str, ProductCard] = {}
    for opp in opps:
        if provider.name != "mock":
            await asyncio.sleep(PAUSE)
        print(f"product: {opp.title}")

        async def make_product(opp=opp):
            events.clear()
            runner = StageRunner(emit, CallBudget(product.MAX_CALLS), provider, product.SYSTEM)
            await product._run(ProductRequest(opportunity=opp), runner)

        try:
            await _patient(make_product, provider)
        except StructuredError as e:
            # 앞서 만든 결과(약 3분치 LLM 호출)는 버리지 않는다 → 이 기회만 빼고 저장
            print(f"  실패({e.code}) → 이 기회는 빼고 계속")
            continue
        card = next(d["product"] for e, d in events if e == "product")
        products[opp.id] = ProductCard.model_validate(card)
    opps = [o for o in opps if o.id in products]  # product가 없는 기회는 예비안에서 뺀다
    if not opps:
        raise StructuredError("no_result", "저장할 결과가 없습니다")

    model = getattr(provider, "model", "") or provider.name
    return snapshot.SnapshotFile(
        company_id=company_id,
        country=req.country,
        snapshot=SnapshotInfo(
            created_at=datetime.now(UTC).isoformat(timespec="seconds"), model=model
        ),
        opportunities=opps,
        products=products,
    )


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--company", required=True)
    ap.add_argument("--count", type=int, default=3)
    ap.add_argument("--provider", help="mock 이면 LLM 없이 흐름만 (저장하지 않음)")
    args = ap.parse_args()
    if args.provider:
        from app.config import settings

        settings.llm_provider = args.provider
        get_provider.cache_clear()
    provider = get_provider()
    snap = await build(args.company, args.count, provider)
    if provider.name == "mock":
        print(
            f"[mock] 기회 {len(snap.opportunities)}건, product {len(snap.products)}건 — 저장 안 함"
        )
        return 0
    path = snapshot.save(snap)
    print(f"저장: {path} (기회 {len(snap.opportunities)}건, product {len(snap.products)}건)")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
