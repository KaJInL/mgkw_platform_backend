from fastapi import APIRouter, Depends
from typing import List

from application.apis.category.series_admin_service import series_admin_service
from application.apis.category.schema.request import (
    QuerySeriesListReq, CreateSeriesReq, UpdateSeriesReq, DeleteSeriesReq,
    GetSeriesDetailReq, GetSeriesTreeReq, GetSeriesChildrenReq, GetSeriesPathReq
)
from application.apis.category.schema.response import SeriesInfoRes, SeriesTreeNodeRes
from application.common.schema import PaginationData, BaseResponse
from application.common.helper import ResponseHelper

series_admin = APIRouter()


@series_admin.get(
    "/admin/series/list",
    summary="查询系列列表",
    description="分页查询系列列表，支持关键词搜索（系列名称）和父级系列筛选",
    response_model=BaseResponse[PaginationData[SeriesInfoRes]],
)
async def query_series_list(req: QuerySeriesListReq = Depends()):
    """
    查询系列列表
    
    Args:
        req: 查询参数对象，包含：
            - page: 页码，从 1 开始
            - pageSize: 每页数量，范围 1-100
            - keyword: 搜索关键词，支持系列名称模糊匹配
            - parentId: 父级系列ID，用于筛选指定父级下的系列
    """
    result = await series_admin_service.query_series_list(req)
    return ResponseHelper.success(result)


@series_admin.post(
    "/admin/series/create",
    summary="新增系列",
    description="创建新系列，可以指定父级系列实现多级系列",
    response_model=BaseResponse[SeriesInfoRes],
)
async def create_series(req: CreateSeriesReq):
    """
    新增系列
    """
    result = await series_admin_service.create_series(req)
    return ResponseHelper.success(result)


@series_admin.post(
    "/admin/series/update",
    summary="修改系列信息",
    description="更新系列的名称或父级系列，自动检测循环引用",
    response_model=BaseResponse[SeriesInfoRes],
)
async def update_series(req: UpdateSeriesReq):
    """
    修改系列信息
    """
    result = await series_admin_service.update_series(req)
    return ResponseHelper.success(result)


@series_admin.post(
    "/admin/series/delete",
    summary="删除系列",
    description="删除系列，支持递归删除子系列",
    response_model=BaseResponse[bool],
)
async def delete_series(req: DeleteSeriesReq):
    """
    删除系列
    """
    result = await series_admin_service.delete_series(req)
    return ResponseHelper.success(result)


@series_admin.get(
    "/admin/series/detail",
    summary="获取系列详情",
    description="根据系列ID获取系列的详细信息（带缓存）",
    response_model=BaseResponse[SeriesInfoRes],
)
async def get_series_detail(req: GetSeriesDetailReq = Depends()):
    """
    获取系列详情
    
    Args:
        req: 查询参数对象，包含：
            - seriesId: 系列 ID
    """
    result = await series_admin_service.get_series_detail(req)
    return ResponseHelper.success(result)


@series_admin.get(
    "/admin/series/tree",
    summary="获取系列树",
    description="获取树形结构的系列列表，支持指定父级和深度限制（带缓存）",
    response_model=BaseResponse[List[SeriesTreeNodeRes]],
)
async def get_series_tree(req: GetSeriesTreeReq = Depends()):
    """
    获取系列树
    
    Args:
        req: 查询参数对象，包含：
            - parentId: 父级系列ID，不传则获取完整树
            - maxDepth: 最大深度限制
    """
    result = await series_admin_service.get_series_tree(req)
    return ResponseHelper.success(result)


@series_admin.get(
    "/admin/series/children",
    summary="获取子系列",
    description="获取指定系列的子系列，支持递归获取所有后代（带缓存）",
    response_model=BaseResponse[List[SeriesInfoRes]],
)
async def get_series_children(req: GetSeriesChildrenReq = Depends()):
    """
    获取子系列
    
    Args:
        req: 查询参数对象，包含：
            - parentId: 父级系列ID
            - recursive: 是否递归获取所有后代
    """
    result = await series_admin_service.get_series_children(req)
    return ResponseHelper.success(result)


@series_admin.get(
    "/admin/series/path",
    summary="获取系列路径",
    description="获取从根节点到指定系列的完整路径（带缓存）",
    response_model=BaseResponse[List[SeriesInfoRes]],
)
async def get_series_path(req: GetSeriesPathReq = Depends()):
    """
    获取系列路径
    
    Args:
        req: 查询参数对象，包含：
            - seriesId: 系列 ID
    """
    result = await series_admin_service.get_series_path(req)
    return ResponseHelper.success(result)

