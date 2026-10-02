"""데모 스냅샷: 미리 실제 LLM으로 만들어 둔 radar·product 결과 (LLM·한도 없이 읽기만).

계약: docs/contracts/radar.md·product.md "snapshot".
파일은 `backend/data/demo/<company_id>.json`이고
`python -m evals.make_demo_snapshot --company <id>`로 만든다.
실시간 생성이 실패했을 때의 예비안이다.
"""

import json
from functools import lru_cache
from pathlib import Path

from fastapi import HTTPException
from pydantic import BaseModel

from app.schemas.product import ProductCard, ProductSnapshot
from app.schemas.radar import Opportunity, RadarSnapshot, SnapshotInfo

DEMO_DIR = Path(__file__).resolve().parents[2] / "data" / "demo"


class SnapshotFile(BaseModel):
    """파일 형식. products는 opportunity id → Product Card."""

    company_id: str
    country: str
    snapshot: SnapshotInfo
    opportunities: list[Opportunity]
    products: dict[str, ProductCard] = {}


@lru_cache
def _load_all() -> dict[str, SnapshotFile]:
    out: dict[str, SnapshotFile] = {}
    for path in sorted(DEMO_DIR.glob("*.json")):
        snap = SnapshotFile.model_validate_json(path.read_text("utf-8"))
        out[snap.company_id] = snap
    return out


def get_radar_snapshot(company_id: str) -> RadarSnapshot:
    snap = _load_all().get(company_id)
    if snap is None:
        raise HTTPException(status_code=404, detail="저장된 결과가 없습니다")
    return RadarSnapshot(**snap.model_dump(exclude={"products"}))


def get_product_snapshot(opportunity_id: str) -> ProductSnapshot:
    for snap in _load_all().values():
        if (card := snap.products.get(opportunity_id)) is not None:
            return ProductSnapshot(snapshot=snap.snapshot, product=card)
    raise HTTPException(status_code=404, detail="저장된 결과가 없습니다")


def save(snap: SnapshotFile) -> Path:
    """생성 스크립트용. 공개 저장소에 커밋되므로 공개 데이터로 만든 결과만 저장한다."""
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    path = DEMO_DIR / f"{snap.company_id}.json"
    path.write_text(
        json.dumps(snap.model_dump(by_alias=True), ensure_ascii=False, indent=1) + "\n", "utf-8"
    )
    _load_all.cache_clear()
    return path
