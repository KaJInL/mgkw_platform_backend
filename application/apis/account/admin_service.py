from application.apis.account.schema.request import CreateSuperUserReq, LoginByPwdReq
from application.apis.account.schema.response import LoginRes
from application.common.base.base_service import CoreService
from application.common.constants import BoolEnum
from application.common.exception.exception import HttpBusinessException
from application.common.exception.http_error_code_enum import HttpErrorCodeEnum
from application.common.models import User
from application.common.utils import PasswordUtils
from application.core.redis_client import redis_client
from application.service.account_service import account_service
from application.service.sys_conf_service import sys_conf_service
from application.service.user_role_service import user_role_service
from application.service.user_service import user_service


class UserAdminService(CoreService):
    """
        管理后台用户service
    """

    async def is_superuser_created(self) -> bool:
        value = await sys_conf_service.get_super_user_create_state()
        if not value:
            return False
        return BoolEnum.is_yes(value)

    async def create_superuser(self, req: CreateSuperUserReq) -> bool:
        """
        创建超级管理员用户
        :param req: 请求对象
        """
        async with  redis_client.lock("create_super_user_lock") as lock:
            # 检查用户是否已经创建
            if await self.is_superuser_created():
                raise HttpBusinessException("超级管理员用户已经创建")

            # 创建用户
            user = await account_service.create_user(req.phone_number, req.password, req.email, is_superuser=True)
        return user is not None

    async def admin_login_by_pwd(self, req: LoginByPwdReq) -> LoginRes:
        """
        管理员用户登录
        :param req: 请求对象
        pass
        """

        # 检查用户是否有管理员角色
        return await account_service.login_by_pwd(req.phone_number, req.password, True)


user_admin_service = UserAdminService()
