from typing import List
from fastapi import APIRouter, Query, HTTPException

from application.apis.common.sys_conf.admin_service import sys_conf_admin_service
from application.apis.common.sys_conf.schema.request import (
    CreateSysConfReq,
    UpdateSysConfReq,
    DeleteSysConfReq
)
from application.apis.common.sys_conf.schema.response import (
    SysConfResponse,
    SysConfOperationResponse
)
from application.common.helper import ResponseHelper, generate_simple_responses
from application.common.schema import BaseResponse, PaginationData
from application.common.exception.http_error_code_enum import HttpErrorCodeEnum

admin = APIRouter()


@admin.post(
    "/admin/conf/create",
    summary="创建系统配置",
    description="创建一个新的系统配置项",
    response_model=BaseResponse[SysConfResponse],
    responses=generate_simple_responses(
        error_codes=[HttpErrorCodeEnum.DATA_DUPLICATE]
    )
)
async def create_config(req: CreateSysConfReq):
    """
    创建系统配置
    """
    result = await sys_conf_admin_service.create_config(req)
    return ResponseHelper.success(result)


@admin.post(
    "/admin/conf/update",
    summary="更新系统配置",
    description="更新系统配置",
    response_model=BaseResponse[SysConfResponse],
    responses=generate_simple_responses()
)
async def update_config(req: UpdateSysConfReq):
    """
    更新系统配置
    """
    result = await sys_conf_admin_service.update_config(req.sys_key, req)
    return ResponseHelper.success(result)


@admin.post(
    "/admin/conf/delete",
    summary="批量删除系统配置",
    description="根据配置 ID 列表批量删除系统配置",
    response_model=BaseResponse[SysConfOperationResponse],
    responses=generate_simple_responses()
)
async def delete_configs(req: DeleteSysConfReq):
    """
    批量删除系统配置
    """
    try:
        success = await sys_conf_admin_service.delete_configs(req.ids)
        return ResponseHelper.success(
            SysConfOperationResponse(success=success, message=f"成功删除 {len(req.ids)} 条配置")
        )
    except ValueError as e:
        return ResponseHelper.error(str(e))


@admin.get(
    "/admin/conf/query",
    summary="查询系统配置列表",
    description="分页查询系统配置列表,支持按 key 模糊搜索",
    response_model=BaseResponse[PaginationData[SysConfResponse]],
    responses=generate_simple_responses()
)
async def query_configs(
        sys_key: str = Query(None, description="配置 key (模糊查询)", alias="sysKey"),
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(10, ge=1, le=100, description="每页数量", alias="pageSize")
):
    """
    查询系统配置列表
    """
    result = await sys_conf_admin_service.query_configs(sys_key, page, page_size)
    return ResponseHelper.success(result)


@admin.get(
    "/admin/conf/get-by-key",
    summary="根据 key 获取配置值",
    description="根据配置 key 获取配置值，只返回配置值字符串",
    response_model=BaseResponse[str],
    responses=generate_simple_responses()
)
async def get_by_key(
        key: str = Query(..., description="配置 key", alias="key")
):
    """
    根据 key 获取配置值
    """
    value = await sys_conf_admin_service.get_by_key(key)
    if value is None:
        raise HTTPException(status_code=404, detail="配置不存在")
    return ResponseHelper.success({"value": value})
