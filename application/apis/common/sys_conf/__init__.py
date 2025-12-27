from fastapi import APIRouter
from .admin_api import admin
from .api import common

sys_conf = APIRouter()
sys_conf.include_router(admin, tags=["管理后台-系统配置接口"])
sys_conf.include_router(common, tags=["系统配置通用接口"])

__all__ = ["sys_conf"]

