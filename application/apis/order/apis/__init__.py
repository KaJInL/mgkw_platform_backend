from fastapi import APIRouter
from .api import order

order_router = APIRouter()
order_router.include_router(order, tags=["订单接口"])

__all__ = [
    "order_router"
]
