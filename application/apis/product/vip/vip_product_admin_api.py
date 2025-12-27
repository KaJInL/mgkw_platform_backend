from fastapi import APIRouter, Depends
from typing import List
from application.apis.product.schema.request import (
    QueryVipProductListReq, CreateVipProductReq, UpdateVipProductReq
)
from application.apis.product.schema.response import VipProductInfoRes
from application.apis.product.vip.service.vip_product_admin_service import vip_product_admin_service
from application.apis.product.vip.service.vip_product_service import vip_product_service
from application.common.helper import ResponseHelper
from application.common.schema import BaseResponse

vip_product_admin = APIRouter(tags=["VIP套餐商品管理接口"])

@vip_product_admin.get(
    "/admin/product/vip/list", 
    summary="查询VIP套餐商品列表",
    response_model=BaseResponse[List[VipProductInfoRes]]
)
async def query_vip_product_list(req: QueryVipProductListReq = Depends()):
    result = await vip_product_admin_service.query_vip_product_list(req)
    return ResponseHelper.success(result)

@vip_product_admin.post(
    "/admin/product/vip/create", 
    summary="新增VIP套餐商品"
)
async def create_vip_product(req: CreateVipProductReq):
    result = await vip_product_admin_service.create_vip_product(req)
    return ResponseHelper.success(result)

@vip_product_admin.post(
    "/admin/product/vip/update", 
    summary="修改VIP套餐商品"
)
async def update_vip_product(req: UpdateVipProductReq):
    result = await vip_product_admin_service.update_vip_product(req)
    return ResponseHelper.success(result)

@vip_product_admin.post(
    "/admin/product/vip/cache/clear", 
    summary="清除VIP产品列表缓存"
)
async def clear_vip_product_cache():
    """
    清除VIP产品列表缓存
    当数据结构变更或需要强制刷新缓存时使用
    """
    await vip_product_service.invalidate_all_cache()
    return ResponseHelper.success({"message": "缓存已清除"})

