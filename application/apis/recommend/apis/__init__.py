from fastapi import APIRouter
from .recommend_admin_api import recommend_admin
from .recommend_api import recommend

recommend_router = APIRouter()
recommend_router.include_router(recommend_admin)
recommend_router.include_router(recommend)

__all__ = [
    "recommend_router"
]
