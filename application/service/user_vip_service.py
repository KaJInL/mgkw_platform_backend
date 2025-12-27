from typing import Optional

from application.common.base import BaseService
from application.common.models import UserVIP


class UserVipService(BaseService[UserVIP]):
    """用户会员权益service"""

    async def get_by_user_id(self, user_id: int) -> Optional[UserVIP]:
        return await self.model_class.filter(user_id=user_id).get_or_none()


user_vip_service = UserVipService()
