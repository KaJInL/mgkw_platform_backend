from typing import Optional, List

from application.common.base import BaseService
from application.common.models import DesignLicensePlan
from application.common.models.design import LicenseType
from application.core.redis_client import redis_client, TimeUnit
from application.core.logger_util import logger


class DesignLicensePlanService(BaseService[DesignLicensePlan]):
    """
    设计授权方案服务
    支持授权方案的 CRUD 操作，带 Redis 缓存优化
    """

    # Redis 缓存键前缀
    CACHE_PREFIX = "design_license_plan"
    CACHE_ITEM_KEY = f"{CACHE_PREFIX}:item"

    # 缓存过期时间（默认30分钟）
    CACHE_EXPIRE = 30
    CACHE_UNIT = TimeUnit.DAYS

    async def get_by_id(self, plan_id: int, select_fields: Optional[List[str]] = None) -> Optional[DesignLicensePlan]:
        """
        根据ID获取授权方案（带缓存）
        
        :param select_fields: 查询的字段
        :param plan_id: 授权方案ID
        :return: 授权方案对象
        """
        cache_key = f"{self.CACHE_ITEM_KEY}:{plan_id}"

        # 尝试从缓存获取
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            logger.debug(f"✅ 从缓存获取授权方案 {plan_id}")
            return self.dict_to_model(cached_data)

        # 从数据库查询（调用父类方法，避免递归）
        plan = await super().get_by_id(plan_id, select_fields)
        if not plan:
            return None

        # 保存到缓存
        await redis_client.set(
            cache_key,
            plan.to_dict(),
            time=self.CACHE_EXPIRE,
            unit=self.CACHE_UNIT
        )
        logger.debug(f"💾 已缓存授权方案 {plan_id}")

        return plan

    async def invalidate_cache(self, plan_id: Optional[int] = None):
        """
        清除授权方案相关缓存
        
        :param plan_id: 授权方案ID（可选）
        """
        # 清除单个方案缓存
        if plan_id:
            cache_key = f"{self.CACHE_ITEM_KEY}:{plan_id}"
            await redis_client.delete(cache_key)
            logger.debug(f"🗑️ 已清除授权方案 {plan_id} 的缓存")

    async def create_plan(self, plan: DesignLicensePlan) -> DesignLicensePlan:
        """
        创建授权方案
        
        :param plan: 授权方案对象（已设置好属性）
        :return: 创建的授权方案对象
        """
        await plan.save()

        # 清除相关缓存
        await self.invalidate_cache(plan_id=plan.id)

        return plan

    async def update_plan(self, plan: DesignLicensePlan) -> Optional[DesignLicensePlan]:
        """
        更新授权方案（带分布式锁，防止并发更新）
        
        :param plan: 要更新的授权方案对象（包含新数据）
        :return: 更新后的授权方案对象
        """
        # 使用分布式锁确保同一授权方案的更新操作串行执行
        lock_key = f"{self.CACHE_PREFIX}:lock:update:{plan.id}"
        async with redis_client.lock(lock_key, expire=10, timeout=5.0):
            # 验证方案是否存在（在锁内重新查询，确保获取最新数据）
            existing = await super().get_by_id(plan.id)
            if not existing:
                return None

            # 更新方案
            await plan.save()

            # 清除缓存
            await self.invalidate_cache(plan_id=plan.id)

            return plan

    async def delete_plan(self, plan_id: int) -> bool:
        """
        删除授权方案（带分布式锁，防止并发删除）
        
        :param plan_id: 授权方案ID
        :return: 是否删除成功
        """
        # 使用分布式锁确保同一授权方案的删除操作串行执行
        lock_key = f"{self.CACHE_PREFIX}:lock:delete:{plan_id}"
        async with redis_client.lock(lock_key, expire=10, timeout=5.0):
            # 获取方案信息（用于清除缓存）
            plan = await super().get_by_id(plan_id)
            if not plan:
                return False

            # 删除方案
            deleted_count = await self.delete_by_id(plan_id)

            if deleted_count > 0:
                # 清除缓存
                await self.invalidate_cache(plan_id=plan_id)
                logger.info(f"🗑️ 授权方案 {plan_id} 已删除")
                return True

            return False

    async def init_system_license_plans(self):
        """
        初始化系统授权方案（使用分布式锁防止并发）
        创建三种固定授权类型：普通授权、买断授权、商业授权
        """
        # 使用分布式锁防止并发初始化
        async with redis_client.lock(
                key=f"{self.CACHE_PREFIX}:init_lock",
                expire=30,  # 锁过期时间30秒
                blocking=True,
                timeout=10.0  # 最多等待10秒
        ):
            logger.info("🔐 获取系统授权方案初始化锁")

            # 定义三种固定授权方案
            system_plans = [
                {
                    "license_type": LicenseType.NORMAL,
                    "description": "普通授权方案"
                },
                {
                    "license_type": LicenseType.BUYOUT,
                    "description": "买断授权方案"
                },
                {
                    "license_type": LicenseType.COMMERCIAL,
                    "description": "商业授权方案"
                },
            ]

            license_types = [plan["license_type"] for plan in system_plans]

            # 查询已有授权方案
            existing_plans = await self.model_class.filter(license_type__in=license_types).all()
            existing_license_types = {plan.license_type for plan in existing_plans}

            # 筛选出需要创建的授权方案
            to_create = [plan for plan in system_plans if plan["license_type"] not in existing_license_types]

            if to_create:
                # 批量创建授权方案
                plans_to_create = [self.model_class(**plan) for plan in to_create]
                await self.model_class.bulk_create(plans_to_create)
                logger.info(f"✨ 批量创建系统授权方案，共 {len(to_create)} 个")
                
                # 清除所有相关缓存（重新查询已创建的方案以获取 id）
                created_plans = await self.model_class.filter(license_type__in=license_types).all()
                for plan in created_plans:
                    await self.invalidate_cache(plan_id=plan.id)
            else:
                logger.info("✅ 系统授权方案已存在，无需创建")


design_license_plan_service = DesignLicensePlanService()
