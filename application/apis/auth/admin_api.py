from fastapi import APIRouter, Depends
from typing import List

from application.apis.auth.role_admin_service import role_admin_service
from application.apis.auth.user_role_admin_service import user_role_admin_service
from application.apis.auth.schema.request import (
    QueryRoleListReq, CreateRoleReq, UpdateRoleReq, DeleteRoleReq, GetRoleDetailReq,
    QueryUserRolesReq, BindUserRoleReq, UnbindUserRoleReq
)
from application.apis.auth.schema.response import RoleInfoRes, UserRolesRes
from application.common.schema import PaginationData
from application.common.helper import ResponseHelper
from application.common.schema import BaseResponse

auth_admin = APIRouter()


# ==================== 角色管理接口 ====================

@auth_admin.get(
    "/admin/auth/role/list",
    summary="查询角色列表",
    description="分页查询角色列表，支持关键词搜索（角色名/描述）和系统角色筛选",
    response_model=BaseResponse[PaginationData[RoleInfoRes]],
)
async def query_role_list(req: QueryRoleListReq = Depends()):
    """
    查询角色列表
    
    Args:
        req: 查询参数对象，包含：
            - page: 页码，从 1 开始
            - pageSize: 每页数量，范围 1-100
            - keyword: 搜索关键词，支持角色名、描述模糊匹配
            - isSystem: 是否为系统角色
    """
    result = await role_admin_service.query_role_list(req)
    return ResponseHelper.success(result)


@auth_admin.get(
    "/admin/auth/role/all",
    summary="获取所有角色",
    description="获取所有角色列表（不分页），用于下拉选择等场景",
    response_model=BaseResponse[List[RoleInfoRes]],
)
async def get_all_roles():
    """
    获取所有角色
    """
    result = await role_admin_service.get_all_roles()
    return ResponseHelper.success(result)


@auth_admin.post(
    "/admin/auth/role/create",
    summary="创建角色",
    description="创建新角色，角色名不能重复",
    response_model=BaseResponse[RoleInfoRes],
)
async def create_role(req: CreateRoleReq):
    """
    创建角色
    
    Args:
        req: 创建参数对象，包含：
            - roleName: 角色名
            - description: 角色描述（可选）
    """
    result = await role_admin_service.create_role(req)
    return ResponseHelper.success(result)


@auth_admin.post(
    "/admin/auth/role/update",
    summary="更新角色",
    description="更新角色信息，系统角色不允许修改",
    response_model=BaseResponse[RoleInfoRes],
)
async def update_role(req: UpdateRoleReq):
    """
    更新角色
    
    Args:
        req: 更新参数对象，包含：
            - roleId: 角色ID
            - roleName: 角色名（可选）
            - description: 角色描述（可选）
    """
    result = await role_admin_service.update_role(req)
    return ResponseHelper.success(result)


@auth_admin.post(
    "/admin/auth/role/delete",
    summary="删除角色",
    description="删除角色，系统角色不允许删除",
    response_model=BaseResponse[bool],
)
async def delete_role(req: DeleteRoleReq):
    """
    删除角色
    
    Args:
        req: 删除参数对象，包含：
            - roleId: 角色ID
    """
    result = await role_admin_service.delete_role(req)
    return ResponseHelper.success(result)


@auth_admin.get(
    "/admin/auth/role/detail",
    summary="获取角色详情",
    description="根据角色ID获取角色的详细信息",
    response_model=BaseResponse[RoleInfoRes],
)
async def get_role_detail(req: GetRoleDetailReq = Depends()):
    """
    获取角色详情
    
    Args:
        req: 查询参数对象，包含：
            - roleId: 角色 ID
    """
    result = await role_admin_service.get_role_detail(req)
    return ResponseHelper.success(result)


# ==================== 用户角色关系管理接口 ====================

@auth_admin.get(
    "/admin/auth/role/user-roles",
    summary="查询用户角色",
    description="查询指定用户拥有的所有角色列表",
    response_model=BaseResponse[UserRolesRes],
)
async def query_user_roles(req: QueryUserRolesReq = Depends()):
    """
    查询用户角色
    
    Args:
        req: 查询参数对象，包含：
            - userId: 用户 ID
    """
    result = await user_role_admin_service.query_user_roles(req)
    return ResponseHelper.success(result)


@auth_admin.post(
    "/admin/auth/role/bind-user-role",
    summary="给用户绑定角色",
    description="为指定用户绑定角色",
    response_model=BaseResponse[bool],
)
async def bind_user_role(req: BindUserRoleReq):
    """
    给用户绑定角色
    """
    result = await user_role_admin_service.bind_user_role(req)
    return ResponseHelper.success(result)


@auth_admin.post(
    "/admin/auth/role/unbind-user-role",
    summary="移除用户角色",
    description="移除用户的指定角色",
    response_model=BaseResponse[bool],
)
async def unbind_user_role(req: UnbindUserRoleReq):
    """
    移除用户角色
    """
    result = await user_role_admin_service.unbind_user_role(req)
    return ResponseHelper.success(result)

