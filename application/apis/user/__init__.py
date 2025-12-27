from fastapi import APIRouter
from .admin_api import user_admin
from .api import user

user_router = APIRouter()
user_router.include_router(user_admin, tags=["用户管理-管理后台接口"])
user_router.include_router(user, tags=["用户管理-接口"])
