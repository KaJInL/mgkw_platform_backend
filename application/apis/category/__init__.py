from fastapi import APIRouter
from .category_admin_api import category_admin
from .series_admin_api import series_admin
from .category_api import category_api

category_router = APIRouter()
category_router.include_router(category_admin, tags=["分类管理-管理后台接口"])
category_router.include_router(series_admin, tags=["系列管理-管理后台接口"])
category_router.include_router(category_api, tags=["分类系列-公开查询接口"])

__all__ = ["category_router"]

