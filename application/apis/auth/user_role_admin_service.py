"""
用户角色关系管理服务
负责处理用户与角色之间的绑定关系
"""
from application.apis.auth.schema.request import QueryUserRolesReq, BindUserRoleReq, UnbindUserRoleReq
from application.apis.auth.schema.response import UserRolesRes, RoleInfoRes
from application.common.exception.exception import HttpBusinessException
from application.service.user_service import user_service
from application.service.role_service import role_service
from application.service.user_role_service import user_role_service
from application.service.account_service import account_service


class UserRoleAdminService:
    """用户角色关系管理服务"""

    async def query_user_roles(self, req: QueryUserRolesReq) -> UserRolesRes:
        """
        查询用户角色
        :param req: 查询请求
        :return: 用户角色列表
        """
        # 使用 user_service 查询用户是否存在
        user = await user_service.get_by_id(req.user_id)
        if not user:
            raise HttpBusinessException(message="用户不存在")

        # 使用 user_role_service 查询用户的所有角色关联
        user_roles = await user_role_service.list(filters={'user_id': req.user_id})
        role_ids = [ur.role_id for ur in user_roles]

        # 使用 role_service 查询角色详情
        roles = []
        if role_ids:
            role_list = await role_service.get_by_ids(role_ids)
            roles = [
                RoleInfoRes(
                    id=role['id'],
                    role_name=role['role_name'],
                    description=role.get('description'),
                    is_system=role['is_system'],
                    created_at=role['created_at']
                )
                for role in role_list
            ]

        return UserRolesRes(user_id=req.user_id, roles=roles)

    async def bind_user_role(self, req: BindUserRoleReq) -> bool:
        """
        给用户绑定角色
        :param req: 绑定请求
        :return: 是否成功
        """
        # 使用 user_service 查询用户是否存在
        user = await user_service.get_by_id(req.user_id)
        if not user:
            raise HttpBusinessException("用户不存在")

        # 使用 role_service 查询角色是否存在
        role = await role_service.get_by_id(req.role_id)
        if not role:
            raise HttpBusinessException("角色不存在")

        # 绑定角色
        await user_role_service.bind_role(req.user_id, req.role_id)

        # 刷新用户的登录缓存，使角色变更立即生效（不强制退出登录）
        await account_service.refresh_user_login_cache(req.user_id)

        return True

    async def unbind_user_role(self, req: UnbindUserRoleReq) -> bool:
        """
        移除用户角色
        :param req: 移除请求
        :return: 是否成功
        """
        # 使用 user_service 查询用户是否存在
        user = await user_service.get_by_id(req.user_id)
        if not user:
            raise HttpBusinessException("用户不存在")

        # 使用 role_service 查询角色是否存在
        role = await role_service.get_by_id(req.role_id)
        if not role:
            raise HttpBusinessException("角色不存在")

        # 移除角色
        success = await user_role_service.unbind_role(req.user_id, req.role_id)
        if not success:
            raise HttpBusinessException("用户未绑定该角色")

        # 刷新用户的登录缓存，使角色变更立即生效（不强制退出登录）
        await account_service.refresh_user_login_cache(req.user_id)

        return True


# 创建全局实例
user_role_admin_service = UserRoleAdminService()

