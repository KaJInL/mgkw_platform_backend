from typing import Optional

from application.common.base.base_service import CoreService
from application.common.models import Design
from application.common.schema import LoginUserInfo
from application.service.account_service import account_service
from application.service.user_design_license_service import user_design_license_service


class DesignAccessService(CoreService):
    async def has_access(self, design: Design) -> bool:
        """
        检查用户是否有查看某个设计作品的权限
        拥有权限的情况有四个:
        1. 是这个作品的创建者
        2. 是平台的VIP会员
        3. 是管理员或超级管理员
        4. 购买了这个作品的授权
        """
        # 先获取登录用户的id
        login_user_info : Optional[LoginUserInfo] = None
        try:
            login_user_info = await account_service.get_login_user_info()
            if not login_user_info:
                return False
        except Exception as e:
            return False

        # 1. 检查是否是这个作品的创建者
        if login_user_info.user.id == design.user_id:
            return True


        # 检查用户是否为管理员或者平台的vip会员
        is_vip = await account_service.is_vip()
        is_admin = await account_service.is_admin()
        if is_vip or is_admin:
            return True

        # 3. 检查用户是否购买
        has_license = await user_design_license_service.has_license(login_user_info.user.id, design.id)
        if has_license:
            return True

        return False


design_access_service = DesignAccessService()
