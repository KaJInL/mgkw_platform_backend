from fastapi import APIRouter
from .wechat_api import wechat

payment_router = APIRouter()
payment_router.include_router(wechat, tags=["微信支付"])

__all__ = ["payment_router"]
