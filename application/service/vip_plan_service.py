from typing import Optional, List

from application.common.base import BaseService
from application.common.models.vip import VIPPlan
from application.core.redis_client import redis_client, TimeUnit
from application.core.logger_util import logger


class VipPlanService(BaseService[VIPPlan]):
    """
    VIP套餐服务
    支持VIP套餐的 CRUD 操作，带 Redis 缓存优化
    """

    # Redis 缓存键前缀
    CACHE_PREFIX = "vip_plan"
    CACHE_ITEM_KEY = f"{CACHE_PREFIX}:item"

    # 缓存过期时间（默认30分钟）
    CACHE_EXPIRE = 30
    CACHE_UNIT = TimeUnit.MINUTES

    async def get_by_id(self, plan_id: int, select_fields: Optional[List[str]] = None) -> Optional[VIPPlan]:
        """
        根据ID获取VIP套餐（带缓存）
        
        :param plan_id: VIP套餐ID
        :param select_fields: 查询的字段
        :return: VIP套餐对象
        """
        cache_key = f"{self.CACHE_ITEM_KEY}:{plan_id}"

        # 尝试从缓存获取
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            logger.debug(f"✅ 从缓存获取VIP套餐 {plan_id}")
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
        logger.debug(f"💾 已缓存VIP套餐 {plan_id}")

        return plan

    async def invalidate_cache(self, plan_id: Optional[int] = None):
        """
        清除VIP套餐相关缓存
        
        :param plan_id: VIP套餐ID（可选）
        """
        if plan_id:
            cache_key = f"{self.CACHE_ITEM_KEY}:{plan_id}"
            await redis_client.delete(cache_key)
            logger.debug(f"🗑️ 已清除VIP套餐 {plan_id} 的缓存")

    async def create_plan(self, plan: VIPPlan) -> VIPPlan:
        """
        创建VIP套餐
        
        :param plan: VIP套餐对象（已设置好属性）
        :return: 创建的VIP套餐对象
        """
        await plan.save()
        logger.info(f"✅ 创建VIP套餐 {plan.id}: {plan.name}")

        # 清除相关缓存
        await self.invalidate_cache(plan_id=plan.id)

        return plan

    async def update_plan(self, plan_id: int, update_data: dict) -> Optional[VIPPlan]:
        """
        更新VIP套餐（带分布式锁，防止并发更新）
        
        :param plan_id: VIP套餐ID
        :param update_data: 要更新的数据
        :return: 更新后的VIP套餐对象
        """
        # 使用分布式锁确保同一VIP套餐的更新操作串行执行
        lock_key = f"{self.CACHE_PREFIX}:lock:update:{plan_id}"
        async with redis_client.lock(lock_key, expire=10, timeout=5.0):
            # 验证套餐是否存在
            existing = await super().get_by_id(plan_id)
            if not existing:
                return None

            # 更新套餐
            for key, value in update_data.items():
                if value is not None:
                    setattr(existing, key, value)
            
            await existing.save()
            logger.info(f"✅ 更新VIP套餐 {plan_id}")

            # 清除缓存
            await self.invalidate_cache(plan_id=plan_id)

            return existing

    async def delete_plan(self, plan_id: int) -> bool:
        """
        删除VIP套餐（带分布式锁，防止并发删除）
        
        :param plan_id: VIP套餐ID
        :return: 是否删除成功
        """
        # 使用分布式锁确保同一VIP套餐的删除操作串行执行
        lock_key = f"{self.CACHE_PREFIX}:lock:delete:{plan_id}"
        async with redis_client.lock(lock_key, expire=10, timeout=5.0):
            # 获取套餐信息
            plan = await super().get_by_id(plan_id)
            if not plan:
                return False

            # 删除套餐
            deleted_count = await self.delete_by_id(plan_id)

            if deleted_count > 0:
                # 清除缓存
                await self.invalidate_cache(plan_id=plan_id)
                logger.info(f"🗑️ VIP套餐 {plan_id} 已删除")
                return True

            return False


vip_plan_service = VipPlanService()

