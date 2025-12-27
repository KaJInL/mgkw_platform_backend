from typing import Optional

from application.common.base import BaseService
from application.common.models import UserAuth, AuthTypeEnum


class UserAuthService(BaseService[UserAuth]):
    """
    第三方授权service
    """

    async def get_user_id_by_wx_miniprogram_openid(self, openid: str) -> Optional[UserAuth]:
        """
        通过微信小程序openid获取用户id
        """
        return await self.model_class.get_or_none(openid=openid)


    async def save_auth_info(self, user_id : str, openid : str,  auth_type: AuthTypeEnum,unionid : str = None):
        """
        保存授权信息
        """
        return await self.model_class.create(user_id=user_id, openid=openid, unionid=unionid, auth_type=auth_type)
user_auth_service = UserAuthService()