from fastapi import APIRouter
from .design_product_admin_api import design_product_admin
from .design_product_api import design_product

design_router = APIRouter()
design_router.include_router(design_product_admin, tags=["设计产品管理后台api"])
design_router.include_router(design_product, tags=["设计产品api"])

__all__ = [
    "design_router"
]
