from typing import List

from application.common.base import BaseService
from application.common.constants import RoleEnum
from application.common.exception.exception import HttpBusinessException
from application.common.models import UserRole, Role
from application.service.role_service import role_service


class UserRoleService(BaseService[UserRole]):
    """
    用户角色service
    """

    async def bind_role(self, user_id: int, role_id: int) -> UserRole:
        """
        绑定用户角色
        :param user_id: 用户ID
        :param role_id: 角色ID
        :return: 用户角色关联对象
        """
        # 检查是否已经绑定
        existing = await self.model_class.filter(user_id=user_id, role_id=role_id).first()
        if existing:
            return existing

        # 创建绑定关系
        user_role = await self.model_class.create(
            user_id=user_id,
            role_id=role_id
        )
        return user_role

    async def bind_roles(self, user_id: int, role_ids: List[int]) -> List[UserRole]:
        """
        批量绑定用户角色
        :param user_id: 用户ID
        :param role_ids: 角色ID列表
        :return: 用户角色关联对象列表
        """
        user_roles = []
        for role_id in role_ids:
            user_role = await self.bind_role(user_id, role_id)
            user_roles.append(user_role)
        return user_roles

    async def unbind_role(self, user_id: int, role_id: int) -> bool:
        """
        解绑用户角色
        :param user_id: 用户ID
        :param role_id: 角色ID
        :return: 是否成功
        """
        deleted_count = await self.model_class.filter(user_id=user_id, role_id=role_id).delete()
        return deleted_count > 0

    async def is_admin(self, user_id: int) -> bool:
        """
        检查用户是否是管理员
        :param user_id: 用户ID
        :return: 是否是管理员
        """

        # 查询出管理员角色id
        roles = await role_service.get_role_by_names([RoleEnum.ADMIN, RoleEnum.SUPER_ADMIN])
        if not roles:
            return False

        role_ids = [role.id for role in roles]
        for role_id in role_ids:
            if await self.has_role(user_id, role_id):
                return True

        return False

    async def has_role(self, user_id: int, role_id: int) -> bool:
        """
        检查用户是否拥有某个角色
        :param user_id: 用户ID
        :param role_id: 角色ID
        :return: 是否拥有
        """
        user_role = await self.model_class.filter(user_id=user_id, role_id=role_id).first()
        return user_role is not None

    async def bind_super_admin_role(self, user_id: int) -> UserRole:
        """
        绑定超级管理员角色
        :param user_id: 用户ID
        :return: 用户角色关联对象
        """
        from application.service.role_service import role_service
        super_admin_role = await role_service.get_role_by_name(RoleEnum.SUPER_ADMIN)
        return await self.bind_role(user_id, super_admin_role.id)

    async def bind_admin_role(self, user_id: int) -> UserRole:
        """
        绑定管理员角色
        :param user_id: 用户ID
        :return: 用户角色关联对象
        """
        from application.service.role_service import role_service
        admin_role = await role_service.get_role_by_name(RoleEnum.ADMIN)
        return await self.bind_role(user_id, admin_role.id)

    async def bind_user_role(self, user_id: int) -> UserRole:
        """
        绑定普通用户角色
        :param user_id: 用户ID
        :return: 用户角色关联对象
        """
        from application.service.role_service import role_service
        user_role = await role_service.get_role_by_name(RoleEnum.USER)
        return await self.bind_role(user_id, user_role.id)

    async def bind_designer_role(self, user_id: int) -> UserRole:
        """
        绑定设计师角色
        :param user_id: 用户ID
        :return: 用户角色关联对象
        """
        from application.service.role_service import role_service
        designer_role = await role_service.get_role_by_name(RoleEnum.DESIGNER)
        return await self.bind_role(user_id, designer_role.id)


user_role_service = UserRoleService()
