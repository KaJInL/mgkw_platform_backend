from fastapi import APIRouter, Depends
from typing import List

from application.apis.product.design.service.design_product_service import design_product_service
from application.apis.product.schema.request import (
    QueryDesignProductListReq, GetDesignProductDetailReq
)
from application.apis.product.schema.response import (
    DesignProductInfoRes, DesignProductDetailRes, PurchasedDesignProductItemRes
)
from application.common.helper import ResponseHelper
from application.common.schema import PaginationData, BaseResponse
from application.service.account_service import account_service

design_product = APIRouter(tags=["设计作品商品前端接口"])

@design_product.get(
    "/product/design/list", 
    summary="前端查询设计作品商品列表",
    response_model=BaseResponse[PaginationData[DesignProductInfoRes]]
)
async def query_design_product_list(req: QueryDesignProductListReq = Depends()):
    result = await design_product_service.query_design_product_list(req)
    return ResponseHelper.success(result)

@design_product.get(
    "/product/design/detail", 
    summary="前端查看设计作品商品详情",
    response_model=BaseResponse[DesignProductDetailRes]
)
async def get_design_product_detail(req: GetDesignProductDetailReq = Depends()):
    result = await design_product_service.get_design_product_detail(req)
    return ResponseHelper.success(result)

@design_product.get(
    "/product/design/purchased",
    summary="查询用户已购买的设计作品商品列表",
    response_model=BaseResponse[List[PurchasedDesignProductItemRes]]
)
async def get_purchased_design_products():
    """
    获取当前用户已购买的所有设计作品商品列表
    返回格式：[{img_url: "", name: "", product_id: ""}]
    """
    # 获取当前登录用户信息
    user_info = await account_service.get_login_user_info()
    
    # 调用 service 层获取已购买的设计作品列表
    result = await design_product_service.get_purchased_design_products(user_info.id)
    
    return ResponseHelper.success(result)




