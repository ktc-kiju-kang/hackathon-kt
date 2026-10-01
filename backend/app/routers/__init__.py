"""라우터 자동 등록. 기능마다 app/routers/<feature>.py 에 `router`를 정의하면
main.py가 /api 아래에 등록한다. 새 기능 추가 시 main.py를 고칠 필요가 없다.
"""

import importlib
import pkgutil

from fastapi import APIRouter


def discover_routers() -> list[APIRouter]:
    routers = []
    for mod in sorted(pkgutil.iter_modules(__path__), key=lambda m: m.name):
        if mod.ispkg or mod.name.startswith("_"):
            continue
        module = importlib.import_module(f"{__name__}.{mod.name}")
        router = getattr(module, "router", None)
        if not isinstance(router, APIRouter):
            raise RuntimeError(
                f"app/routers/{mod.name}.py 에 `router = APIRouter(...)`가 없습니다. "
                "헬퍼 모듈이면 파일명을 _로 시작하거나 services/로 옮기세요."
            )
        routers.append(router)
    return routers
