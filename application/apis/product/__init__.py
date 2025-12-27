from fastapi import APIRouter

from .design import design_router
from .vip import vip_router

product_router = APIRouter()
product_router.include_router(design_router)
product_router.include_router(vip_router)
__all__ = [
    "product_router",
]
