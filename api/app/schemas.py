# docs/CONTRACTS.md 와 1:1로 맞춘다. 변경 시 계약 문서 먼저 수정.
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class Health(BaseModel):
    status: Literal["ok"]
    time: datetime
