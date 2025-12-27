from fastapi import APIRouter
from .admin_api import auth_admin

auth_router = APIRouter()
auth_router.include_router(auth_admin, tags=["权限管理-管理后台接口"])

