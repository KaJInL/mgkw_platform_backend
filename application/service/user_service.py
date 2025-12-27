from typing import Optional

from application.common.base import BaseService
from application.common.models import User
from application.common.utils import PasswordUtils
from application.core.redis_client import redis_client
from application.service.sys_conf_service import sys_conf_service


class UserService(BaseService[User]):
    """
    用户service
    """

    async def get_user_by_phone(self, phone: str) -> Optional[User]:
        """
        使用手机号获取用户
        :param phone:  手机号
        """
        return await self.get_one(phone=phone)

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        使用邮箱获取用户
        :param email: 邮箱地址
        """
        return await self.get_one(email=email)




user_service = UserService()
