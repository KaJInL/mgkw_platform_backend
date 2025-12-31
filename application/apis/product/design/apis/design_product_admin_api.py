from fastapi import APIRouter, Depends, Query
from application.apis.product.design.service.design_product_admin_service import design_product_admin_service
from application.apis.product.schema.request import (
    QueryDesignProductListReq, AuditDesignProductReq, GetDesignProductDetailReq, UpdateSkuReq
)
from application.apis.product.schema.response import DesignProductInfoRes, DesignProductDetailRes, ProductSimpleInfoRes
from application.common.helper import ResponseHelper
from application.common.schema import PaginationData, BaseResponse
from typing import List, Optional

design_product_admin = APIRouter(tags=["设计作品商品管理接口"])

@design_product_admin.get(
    "/admin/product/design/list", 
    summary="查询设计作品商品列表",
    response_model=BaseResponse[PaginationData[DesignProductInfoRes]]
)
async def query_design_product_list(req: QueryDesignProductListReq = Depends()):
    result = await design_product_admin_service.query_design_product_list(req)
    return ResponseHelper.success(result)

@design_product_admin.post(
    "/admin/product/design/audit", 
    summary="审核设计作品商品"
)
async def audit_design_product(req: AuditDesignProductReq):
    result = await design_product_admin_service.audit_design_product(req)
    return ResponseHelper.success(result)

@design_product_admin.get(
    "/admin/product/design/detail", 
    summary="查看设计作品商品详情",
    response_model=BaseResponse[DesignProductDetailRes]
)
async def get_design_product_detail(req: GetDesignProductDetailReq = Depends()):
    result = await design_product_admin_service.get_design_product_detail(req)
    return ResponseHelper.success(result)

@design_product_admin.post(
    "/admin/product/design/sku/update", 
    summary="更新设计作品商品SKU"
)
async def update_design_product_sku(req: UpdateSkuReq):
    result = await design_product_admin_service.update_sku(req)
    return ResponseHelper.success(result)

@design_product_admin.get(
    "/admin/product/search",
    summary="搜索商品（仅返回id、封面图片、名称）",
    response_model=BaseResponse[PaginationData[ProductSimpleInfoRes]]
)
async def search_product_by_keyword(
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    page_no: int = Query(1, description="页码", gt=0, alias="pageNo"),
    page_size: int = Query(10, description="每页数量", gt=0, le=100, alias="pageSize")
):
    result = await design_product_admin_service.search_product_by_keyword(
        keyword=keyword,
        page_no=page_no,
        page_size=page_size
    )
    return ResponseHelper.success(result)
