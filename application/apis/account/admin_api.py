from fastapi import APIRouter

from application.apis.account.admin_service import user_admin_service
from application.apis.account.schema.request import CreateSuperUserReq, InvalidateTokenReq, InvalidateUserTokensReq
from application.apis.account.schema.response import SuperuserStatusRes
from application.common.helper import ResponseHelper
from application.common.schema import BaseResponse
from application.service.account_service import account_service

admin = APIRouter()


@admin.get(
    "/admin/account/is-superuser-created",
    summary="检查超级用户是否已创建",
    description="检查系统中是否已经创建了超级用户账号。用于判断系统是否需要进行初始化配置。",
    response_model=BaseResponse[SuperuserStatusRes],
)
async def check_superuser():
    """
    检查超级用户是否已创建
    """
    return ResponseHelper.success(
        SuperuserStatusRes(is_superuser_created=await user_admin_service.is_superuser_created()))


@admin.post(
    "/admin/account/create-superuser",
    summary="创建超级管理员用户",
    response_model=BaseResponse,
)
async def create_superuser(req: CreateSuperUserReq):
    """
    创建超级管理员用户
    """
    return ResponseHelper.success(await user_admin_service.create_superuser(req))

@admin.post(
    "/admin/account/invalidate-token",
    summary="手动失效指定 token",
    description="管理员手动将指定的 token 加入黑名单，使其立即失效。仅超级管理员可调用。",
    response_model=BaseResponse[bool],
)
async def invalidate_token(req: InvalidateTokenReq):
    """
    手动失效指定的 token
    
    将指定的 token 加入黑名单，使其立即失效。
    适用场景：
    - 发现某个 token 被盗用或滥用
    - 需要强制某个会话下线
    """
    success = await account_service.invalidate_token(req.token)
    return ResponseHelper.success(success)


@admin.post(
    "/admin/account/invalidate-user-tokens",
    summary="手动失效用户所有 token",
    description="管理员手动清除指定用户的登录信息，使其所有 token 立即失效。仅超级管理员可调用。",
    response_model=BaseResponse[bool],
)
async def invalidate_user_tokens(req: InvalidateUserTokensReq):
    """
    手动失效指定用户的所有 token
    
    清除 Redis 中该用户的登录信息缓存，使其所有 token 立即失效。
    适用场景：
    - 需要强制用户下线（如安全事件）
    - 用户权限变更后需要重新登录
    - 用户账号被封禁或删除
    """
    success = await account_service.invalidate_user_all_tokens(req.user_id)
    return ResponseHelper.success(success)
