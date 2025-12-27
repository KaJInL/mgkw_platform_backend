from fastapi.routing import APIRouter

common_router = APIRouter()

from .api import common

common_router.include_router(common)

# 子路由
from .sys_conf import sys_conf

common_router.include_router(sys_conf)

__all__ = ["common_router"]
