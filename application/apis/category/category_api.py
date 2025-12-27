from fastapi import APIRouter, Query
from typing import List, Optional

from application.apis.category.category_service import category_public_service
from application.apis.category.schema.response import (
    CategoryInfoRes, CategoryTreeNodeRes, SeriesInfoRes, SeriesTreeNodeRes
)
from application.common.schema import BaseResponse
from application.common.helper import ResponseHelper

category_api = APIRouter()


@category_api.get(
    "/category/list",
    summary="获取分类列表",
    description="获取分类列表，支持关键词搜索（分类名称）和父级分类筛选",
    response_model=BaseResponse[List[CategoryInfoRes]],
)
async def get_category_list(
    keyword: Optional[str] = Query(None, description="搜索关键词（分类名称）"),
    parentId: Optional[int] = Query(None, description="父级分类ID")
):
    """
    获取分类列表
    
    Args:
        keyword: 搜索关键词，支持分类名称模糊匹配
        parentId: 父级分类ID，用于筛选指定父级下的分类
    """
    from application.apis.category.schema.request import QueryCategoryListReq
    req = QueryCategoryListReq(keyword=keyword, parent_id=parentId)
    result = await category_public_service.get_category_list(req)
    return ResponseHelper.success(result)


@category_api.get(
    "/category/tree",
    summary="获取分类树",
    description="获取树形结构的分类列表，支持指定父级和深度限制（带缓存）",
    response_model=BaseResponse[List[CategoryTreeNodeRes]],
)
async def get_category_tree(
    parentId: Optional[int] = Query(None, description="父级分类ID，不传则获取完整树"),
    maxDepth: Optional[int] = Query(None, description="最大深度限制")
):
    """
    获取分类树
    
    Args:
        parentId: 父级分类ID，不传则获取完整树
        maxDepth: 最大深度限制
    """
    from application.apis.category.schema.request import GetCategoryTreeReq
    req = GetCategoryTreeReq(parent_id=parentId, max_depth=maxDepth)
    result = await category_public_service.get_category_tree(req)
    return ResponseHelper.success(result)


@category_api.get(
    "/series/list",
    summary="获取系列列表",
    description="获取系列列表，支持关键词搜索（系列名称）和父级系列筛选",
    response_model=BaseResponse[List[SeriesInfoRes]],
)
async def get_series_list(
    keyword: Optional[str] = Query(None, description="搜索关键词（系列名称）"),
    parentId: Optional[int] = Query(None, description="父级系列ID")
):
    """
    获取系列列表
    
    Args:
        keyword: 搜索关键词，支持系列名称模糊匹配
        parentId: 父级系列ID，用于筛选指定父级下的系列
    """
    from application.apis.category.schema.request import QuerySeriesListReq
    req = QuerySeriesListReq(keyword=keyword, parent_id=parentId)
    result = await category_public_service.get_series_list(req)
    return ResponseHelper.success(result)


@category_api.get(
    "/series/tree",
    summary="获取系列树",
    description="获取树形结构的系列列表，支持指定父级和深度限制（带缓存）",
    response_model=BaseResponse[List[SeriesTreeNodeRes]],
)
async def get_series_tree(
    parentId: Optional[int] = Query(None, description="父级系列ID，不传则获取完整树"),
    maxDepth: Optional[int] = Query(None, description="最大深度限制")
):
    """
    获取系列树
    
    Args:
        parentId: 父级系列ID，不传则获取完整树
        maxDepth: 最大深度限制
    """
    from application.apis.category.schema.request import GetSeriesTreeReq
    req = GetSeriesTreeReq(parent_id=parentId, max_depth=maxDepth)
    result = await category_public_service.get_series_tree(req)
    return ResponseHelper.success(result)

