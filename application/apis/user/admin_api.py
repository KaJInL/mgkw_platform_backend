from fastapi import APIRouter, Depends

from application.apis.user.user_admin_service import user_admin_service
from application.apis.user.schema.request import (
    QueryUserListReq, CreateUserReq, UpdateUserReq, DisableUserReq, GetUserDetailReq
)
from application.apis.user.schema.response import UserInfoRes
from application.common.schema import PaginationData
from application.common.helper import ResponseHelper
from application.common.schema import BaseResponse

user_admin = APIRouter()


@user_admin.get(
    "/admin/user/list",
    summary="查询用户列表",
    description="分页查询用户列表，支持关键词搜索（手机号/邮箱/昵称/用户名）和状态筛选",
    response_model=BaseResponse[PaginationData[UserInfoRes]],
)
async def query_user_list(req: QueryUserListReq = Depends()):
    """
    查询用户列表
    
    Args:
        req: 查询参数对象，包含：
            - page: 页码，从 1 开始
            - pageSize: 每页数量，范围 1-100
            - keyword: 搜索关键词，支持用户名、昵称、手机号、邮箱模糊匹配
            - state: 用户状态：0-禁用，1-启用
    """
    result = await user_admin_service.query_user_list(req)
    return ResponseHelper.success(result)


@user_admin.post(
    "/admin/user/create",
    summary="新增用户",
    description="创建新用户，需要提供手机号或邮箱，密码必须符合强度要求",
    response_model=BaseResponse[UserInfoRes],
)
async def create_user(req: CreateUserReq):
    """
    新增用户
    """
    result = await user_admin_service.create_user(req)
    return ResponseHelper.success(result)


@user_admin.post(
    "/admin/user/update",
    summary="修改用户信息",
    description="更新用户的基本信息，如手机号、邮箱、昵称、用户名、头像等",
    response_model=BaseResponse[UserInfoRes],
)
async def update_user(req: UpdateUserReq):
    """
    修改用户信息
    """
    result = await user_admin_service.update_user(req)
    return ResponseHelper.success(result)


@user_admin.post(
    "/admin/user/disable",
    summary="禁用/启用用户",
    description="设置用户状态为禁用或启用。禁用后用户无法登录，且会清除所有登录 token。不能禁用超级管理员。",
    response_model=BaseResponse[bool],
)
async def disable_user(req: DisableUserReq):
    """
    禁用/启用用户
    """
    result = await user_admin_service.disable_user(req)
    return ResponseHelper.success(result)


@user_admin.get(
    "/admin/user/detail",
    summary="获取用户详情",
    description="根据用户ID获取用户的详细信息",
    response_model=BaseResponse[UserInfoRes],
)
async def get_user_detail(req: GetUserDetailReq = Depends()):
    """
    获取用户详情
    
    Args:
        req: 查询参数对象，包含：
            - userId: 用户 ID
    """
    result = await user_admin_service.get_user_detail(req)
    return ResponseHelper.success(result)
