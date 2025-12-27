from fastapi import APIRouter, Depends
from typing import List

from application.apis.category.category_admin_service import category_admin_service
from application.apis.category.schema.request import (
    QueryCategoryListReq, CreateCategoryReq, UpdateCategoryReq, DeleteCategoryReq,
    GetCategoryDetailReq, GetCategoryTreeReq, GetCategoryChildrenReq, GetCategoryPathReq
)
from application.apis.category.schema.response import CategoryInfoRes, CategoryTreeNodeRes
from application.common.schema import PaginationData, BaseResponse
from application.common.helper import ResponseHelper

category_admin = APIRouter()


@category_admin.get(
    "/admin/category/list",
    summary="查询分类列表",
    description="分页查询分类列表，支持关键词搜索（分类名称）和父级分类筛选",
    response_model=BaseResponse[PaginationData[CategoryInfoRes]],
)
async def query_category_list(req: QueryCategoryListReq = Depends()):
    """
    查询分类列表
    
    Args:
        req: 查询参数对象，包含：
            - page: 页码，从 1 开始
            - pageSize: 每页数量，范围 1-100
            - keyword: 搜索关键词，支持分类名称模糊匹配
            - parentId: 父级分类ID，用于筛选指定父级下的分类
    """
    result = await category_admin_service.query_category_list(req)
    return ResponseHelper.success(result)


@category_admin.post(
    "/admin/category/create",
    summary="新增分类",
    description="创建新分类，可以指定父级分类实现多级分类",
    response_model=BaseResponse[CategoryInfoRes],
)
async def create_category(req: CreateCategoryReq):
    """
    新增分类
    """
    result = await category_admin_service.create_category(req)
    return ResponseHelper.success(result)


@category_admin.post(
    "/admin/category/update",
    summary="修改分类信息",
    description="更新分类的名称或父级分类，自动检测循环引用",
    response_model=BaseResponse[CategoryInfoRes],
)
async def update_category(req: UpdateCategoryReq):
    """
    修改分类信息
    """
    result = await category_admin_service.update_category(req)
    return ResponseHelper.success(result)


@category_admin.post(
    "/admin/category/delete",
    summary="删除分类",
    description="删除分类，支持递归删除子分类",
    response_model=BaseResponse[bool],
)
async def delete_category(req: DeleteCategoryReq):
    """
    删除分类
    """
    result = await category_admin_service.delete_category(req)
    return ResponseHelper.success(result)


@category_admin.get(
    "/admin/category/detail",
    summary="获取分类详情",
    description="根据分类ID获取分类的详细信息（带缓存）",
    response_model=BaseResponse[CategoryInfoRes],
)
async def get_category_detail(req: GetCategoryDetailReq = Depends()):
    """
    获取分类详情
    
    Args:
        req: 查询参数对象，包含：
            - categoryId: 分类 ID
    """
    result = await category_admin_service.get_category_detail(req)
    return ResponseHelper.success(result)


@category_admin.get(
    "/admin/category/tree",
    summary="获取分类树",
    description="获取树形结构的分类列表，支持指定父级和深度限制（带缓存）",
    response_model=BaseResponse[List[CategoryTreeNodeRes]],
)
async def get_category_tree(req: GetCategoryTreeReq = Depends()):
    """
    获取分类树
    
    Args:
        req: 查询参数对象，包含：
            - parentId: 父级分类ID，不传则获取完整树
            - maxDepth: 最大深度限制
    """
    result = await category_admin_service.get_category_tree(req)
    return ResponseHelper.success(result)


@category_admin.get(
    "/admin/category/children",
    summary="获取子分类",
    description="获取指定分类的子分类，支持递归获取所有后代（带缓存）",
    response_model=BaseResponse[List[CategoryInfoRes]],
)
async def get_category_children(req: GetCategoryChildrenReq = Depends()):
    """
    获取子分类
    
    Args:
        req: 查询参数对象，包含：
            - parentId: 父级分类ID
            - recursive: 是否递归获取所有后代
    """
    result = await category_admin_service.get_category_children(req)
    return ResponseHelper.success(result)


@category_admin.get(
    "/admin/category/path",
    summary="获取分类路径",
    description="获取从根节点到指定分类的完整路径（带缓存）",
    response_model=BaseResponse[List[CategoryInfoRes]],
)
async def get_category_path(req: GetCategoryPathReq = Depends()):
    """
    获取分类路径
    
    Args:
        req: 查询参数对象，包含：
            - categoryId: 分类 ID
    """
    result = await category_admin_service.get_category_path(req)
    return ResponseHelper.success(result)

