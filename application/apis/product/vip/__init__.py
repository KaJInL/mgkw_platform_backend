from fastapi import APIRouter
from .vip_product_admin_api import vip_product_admin
from .vip_product_api import vip_product

vip_router = APIRouter()
vip_router.include_router(vip_product_admin, tags=["VIP套餐商品管理后台api"])
vip_router.include_router(vip_product, tags=["VIP套餐商品api"])

__all__ = [
    "vip_router",
]