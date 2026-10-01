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
        routers.append(importlib.import_module(f"{__name__}.{mod.name}").router)
    return routers
