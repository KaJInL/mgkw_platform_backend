from fastapi.routing import APIRouter
from .admin_api import admin
from .api import api

account_router = APIRouter()
account_router.include_router(admin, tags=["用户认证-管理后台相关接口"])
account_router.include_router(api, tags=["用户认证-接口"])
