from fastapi import APIRouter, Depends
from application.apis.product.design.service.design_product_service import design_product_service
from application.apis.product.schema.request import (
    QueryDesignProductListReq, GetDesignProductDetailReq
)
from application.apis.product.schema.response import DesignProductInfoRes, DesignProductDetailRes
from application.common.helper import ResponseHelper
from application.common.schema import PaginationData, BaseResponse

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




