from typing import Optional

from application.common.base import BaseService
from application.common.constants import RoleEnum, RoleNameEnum
from application.common.exception.exception import HttpBusinessException
from application.common.models import Role
from application.core.redis_client import redis_client, TimeUnit
from application.core.logger_util import logger


class RoleService(BaseService[Role]):
    """
    角色service
    """

    # Redis 缓存键
    CACHE_KEY_ALL_ROLES = "role:all"

    # 缓存过期时间（24小时）
    CACHE_TTL_HOURS = 24

    async def _get_all_roles_from_cache(self) -> Optional[list[Role]]:
        """从缓存获取所有角色"""
        try:
            cached_data = await redis_client.get(self.CACHE_KEY_ALL_ROLES)
            if cached_data:
                logger.debug(f"🎯 命中角色缓存，共 {len(cached_data)} 个")
                return [self.dict_to_model(data) for data in cached_data]
            return None
        except Exception as e:
            logger.warning(f"⚠️ 获取角色缓存失败: {e}")
            return None

    async def _cache_all_roles(self, roles: list[Role]):
        """缓存所有角色"""
        try:
            roles_data = [role.to_dict() for role in roles]
            await redis_client.set(
                self.CACHE_KEY_ALL_ROLES,
                roles_data,
                time=self.CACHE_TTL_HOURS,
                unit=TimeUnit.HOURS
            )
            logger.debug(f"✅ 缓存所有角色，共 {len(roles)} 个")
        except Exception as e:
            logger.warning(f"⚠️ 缓存角色失败: {e}")

    async def _invalidate_all_roles_cache(self):
        """清除所有角色缓存"""
        try:
            await redis_client.delete(self.CACHE_KEY_ALL_ROLES)
            logger.debug("🗑️ 清除角色缓存")
        except Exception as e:
            logger.warning(f"⚠️ 清除角色缓存失败: {e}")

    async def _get_all_roles(self) -> list[Role]:
        """获取所有角色（优先从缓存）"""
        # 1. 先尝试从缓存获取
        cached_roles = await self._get_all_roles_from_cache()
        if cached_roles is not None:
            return cached_roles

        # 2. 缓存未命中，查询数据库
        roles = await self.model_class.all()
        
        # 3. 缓存所有角色
        await self._cache_all_roles(roles)
        
        return roles

    async def get_or_create_role(self, role_name: str, description: str = None, is_system: bool = False) -> Role:
        """
        获取或创建角色（带缓存优化）
        :param role_name: 角色名称
        :param description: 角色描述
        :param is_system: 是否为系统角色
        :return: 角色对象
        """
        # 1. 先从缓存中查找
        all_roles = await self._get_all_roles()
        for role in all_roles:
            if role.role_name == role_name:
                return role

        # 2. 缓存中不存在，创建新角色
        role = await self.model_class.create(
            role_name=role_name,
            description=description or role_name,
            is_system=is_system
        )
        logger.info(f"✨ 创建新角色: {role_name}")

        # 3. 清除缓存，下次会重新加载
        await self._invalidate_all_roles_cache()

        return role

    async def get_role_by_name(self, role_name: str) -> Role:
        """
        根据角色名称获取角色（带缓存优化）
        :param role_name: 角色名称
        :return: 角色对象
        """
        # 从缓存的所有角色中查找
        all_roles = await self._get_all_roles()
        for role in all_roles:
            if role.role_name == role_name:
                return role

        raise HttpBusinessException(f"角色 {role_name} 不存在")

    async def get_role_by_names(self, role_names: list[str]) -> Optional[list[Role]]:
        """
        根据角色名称列表获取角色列表（带缓存优化）
        :param role_names: 角色名称列表
        :return: 角色列表
        """
        if not role_names:
            return []

        # 从缓存的所有角色中过滤
        all_roles = await self._get_all_roles()
        role_names_set = set(role_names)
        
        return [role for role in all_roles if role.role_name in role_names_set]

    async def get_system_roles(self) -> list[Role]:
        """
        获取所有系统角色（带缓存优化）
        :return: 系统角色列表
        """
        # 从缓存的所有角色中过滤系统角色
        all_roles = await self._get_all_roles()
        return [role for role in all_roles if role.is_system]

    async def init_system_roles(self):
        """
        初始化系统角色（使用分布式锁防止并发）
        批量创建超级管理员、管理员、普通用户、设计师等系统角色
        """
        # 使用分布式锁防止并发初始化
        async with redis_client.lock(
                key="init_role_lock",
                expire=30,  # 锁过期时间30秒
                blocking=True,
                timeout=10.0  # 最多等待10秒
        ):
            logger.info("🔐 获取系统角色初始化锁")

            system_roles = [
                {"role_name": RoleEnum.SUPER_ADMIN, "description": RoleNameEnum.SUPER_ADMIN, "is_system": True},
                {"role_name": RoleEnum.ADMIN, "description": RoleNameEnum.ADMIN, "is_system": True},
                {"role_name": RoleEnum.USER, "description": RoleNameEnum.USER, "is_system": True},
                {"role_name": RoleEnum.DESIGNER, "description": RoleNameEnum.DESIGNER, "is_system": True},
                {"role_name": RoleEnum.COMPANY_DESIGNER, "description": RoleNameEnum.COMPANY_DESIGNER, "is_system": True},
            ]

            role_names = [r["role_name"] for r in system_roles]

            # 查询已有角色
            existing_roles = await self.model_class.filter(role_name__in=role_names).all()
            existing_role_names = {r.role_name for r in existing_roles}

            # 筛选出需要创建的角色
            to_create = [r for r in system_roles if r["role_name"] not in existing_role_names]

            if to_create:
                await self.model_class.bulk_create([self.model_class(**r) for r in to_create])
                logger.info(f"✨ 批量创建系统角色，共 {len(to_create)} 个")
            else:
                logger.info("✅ 系统角色已存在，无需创建")

            # 清除缓存，下次会重新加载所有角色
            await self._invalidate_all_roles_cache()

    async def update_role(self, role_id: int, **kwargs) -> Role:
        """
        更新角色信息（清除相关缓存）
        :param role_id: 角色ID
        :param kwargs: 更新字段
        :return: 更新后的角色对象
        """
        role = await self.model_class.filter(id=role_id).first()
        if not role:
            raise HttpBusinessException(f"角色 ID={role_id} 不存在")

        # 更新角色
        await role.update_from_dict(kwargs)
        await role.save()

        # 清除缓存，下次会重新加载所有角色
        await self._invalidate_all_roles_cache()

        logger.info(f"📝 更新角色: {role.role_name}")
        return role

    async def delete_role(self, role_id: int):
        """
        删除角色（清除相关缓存）
        :param role_id: 角色ID
        """
        role = await self.model_class.filter(id=role_id).first()
        if not role:
            raise HttpBusinessException(f"角色 ID={role_id} 不存在")

        if role.is_system:
            raise HttpBusinessException("系统角色不能删除")

        role_name = role.role_name

        # 删除角色
        await role.delete()

        # 清除缓存，下次会重新加载所有角色
        await self._invalidate_all_roles_cache()

        logger.info(f"🗑️ 删除角色: {role_name}")


role_service = RoleService()
