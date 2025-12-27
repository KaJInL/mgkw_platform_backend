from fastapi import APIRouter
from typing import List
from application.apis.product.vip.service.vip_product_service import vip_product_service
from application.apis.product.schema.response import VipProductInfoRes
from application.common.helper import ResponseHelper
from application.common.schema import BaseResponse

vip_product = APIRouter(tags=["VIP套餐商品前端接口"])

@vip_product.get(
    "/product/vip/list", 
    summary="前端查询VIP套餐商品列表",
    response_model=BaseResponse[List[VipProductInfoRes]]
)
async def query_vip_product_list():
    """
    前端查询VIP套餐商品列表
    不接受查询参数，直接返回全部已审核通过且已上架的VIP商品
    使用Redis缓存优化
    """
    result = await vip_product_service.query_vip_product_list()
    return ResponseHelper.success(result)

