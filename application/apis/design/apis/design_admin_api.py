from fastapi import APIRouter, Query
from typing import Optional

from application.apis.design.schema import (
    UpdateDesignLicensePlanReq,
    DesignLicensePlanInfoRes
)
from application.common.schema import PaginationData, BaseResponse
from application.common.helper import ResponseHelper
from application.common.exception.exception import HttpBusinessException
from application.common.exception.http_error_code_enum import HttpErrorCodeEnum
from application.service.design_license_plan_service import design_license_plan_service
from application.common.models.design import DesignLicensePlan, LicenseType

design_admin_router = APIRouter(tags=["设计套餐管理"])


@design_admin_router.post(
    "/admin/design-plan/update",
    summary="更新设计授权方案",
    description="更新三种固定授权方案（普通授权、买断授权、商业授权）的描述，不能修改授权类型",
    response_model=BaseResponse[DesignLicensePlanInfoRes],
)
async def update_design_license_plan(req: UpdateDesignLicensePlanReq):
    """
    更新设计授权方案
    
    只能更新三种固定授权类型（普通授权、买断授权、商业授权）的描述
    不能修改授权类型，不能新增或删除授权方案
    
    Args:
        req: 授权方案更新请求对象
    """
    # 获取现有方案
    existing = await design_license_plan_service.get_by_id(req.id)
    if not existing:
        raise HttpBusinessException(
            HttpErrorCodeEnum.ERROR,
            "授权方案不存在"
        )

    # 验证授权类型是否为三种固定类型之一
    if existing.license_type not in [LicenseType.NORMAL, LicenseType.BUYOUT, LicenseType.COMMERCIAL]:
        raise HttpBusinessException(
            HttpErrorCodeEnum.ERROR,
            "只能修改三种固定授权类型（普通授权、买断授权、商业授权）"
        )

    # 如果请求中包含了 license_type，不允许修改
    update_data = req.model_dump(exclude_unset=True, exclude={"id"}, by_alias=False)
    if "license_type" in update_data:
        raise HttpBusinessException(
            HttpErrorCodeEnum.ERROR,
            "不能修改授权类型"
        )

    # 更新属性（只更新描述和基础定价）
    for key, value in update_data.items():
        if key in ["description", "base_price"]:
            setattr(existing, key, value)

    # 更新授权方案
    plan = await design_license_plan_service.update_plan(existing)

    if not plan:
        raise HttpBusinessException(
            HttpErrorCodeEnum.ERROR,
            "更新失败"
        )

    return ResponseHelper.success(DesignLicensePlanInfoRes.model_validate(plan))


@design_admin_router.get(
    "/admin/design-plan/detail",
    summary="获取设计授权方案详情",
    description="获取授权方案的详细信息（带缓存）",
    response_model=BaseResponse[DesignLicensePlanInfoRes],
)
async def get_design_license_plan_detail(
    id: int = Query(..., description="授权方案ID", gt=0)
):
    """
    获取设计授权方案详情
    
    Args:
        id: 授权方案ID
    """
    plan = await design_license_plan_service.get_by_id(id)

    if not plan:
        raise HttpBusinessException(HttpErrorCodeEnum.ERROR, "授权方案不存在")

    return ResponseHelper.success(DesignLicensePlanInfoRes.model_validate(plan))


@design_admin_router.get(
    "/admin/design-plan/list",
    summary="查询设计授权方案列表",
    description="查询三种固定授权方案列表（普通授权、买断授权、商业授权），支持授权类型筛选",
    response_model=BaseResponse[PaginationData[DesignLicensePlanInfoRes]],
)
async def query_design_license_plan_list(
    page: int = Query(1, description="页码", ge=1),
    page_size: int = Query(10, description="每页数量", ge=1, le=100, alias="pageSize"),
    license_type: Optional[LicenseType] = Query(None, description="授权类型筛选", alias="licenseType"),
):
    """
    查询设计授权方案列表
    
    只返回三种固定授权类型（普通授权、买断授权、商业授权）
    
    Args:
        page: 页码
        page_size: 每页数量
        license_type: 授权类型筛选（只能为普通授权、买断授权、商业授权之一）
    """
    # 构建查询，只查询三种固定授权类型
    fixed_license_types = [LicenseType.NORMAL, LicenseType.BUYOUT, LicenseType.COMMERCIAL]
    query = DesignLicensePlan.filter(license_type__in=fixed_license_types)

    # 授权类型筛选（验证是否为固定类型之一）
    if license_type:
        if license_type not in fixed_license_types:
            raise HttpBusinessException(
                HttpErrorCodeEnum.ERROR,
                "只能查询三种固定授权类型（普通授权、买断授权、商业授权）"
            )
        query = query.filter(license_type=license_type)

    # 分页查询
    result = await design_license_plan_service.paginate(
        query=query,
        page_no=page,
        page_size=page_size,
        order_by=["-created_at"]
    )

    return ResponseHelper.success(result)


