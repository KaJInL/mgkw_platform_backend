from itertools import product

from application.common.base import BaseService
from application.common.models import UserDesignLicense, DesignLicensePlan, LicenseType, SKU
from application.common.models.design import DesignState
from application.core.lifespan import logger
from application.core.redis_client import redis_client, TimeUnit
from application.service.design_service import design_service
from application.service.product_service import product_service


class UserDesignLicenseService(BaseService[UserDesignLicense]):
    CACHE_KEY = "user_design_license:"

    async def has_license(self, user_id: int, design_id: int) -> bool:
        """
        检查用户是否有授权
        """
        has_license = await redis_client.get(f"{self.CACHE_KEY}{user_id}:{design_id}")
        if has_license:
            return True
        result = await self.model_class.filter(user_id=user_id, design_id=design_id).get_or_none()
        if not result:
            await redis_client.set(f"{self.CACHE_KEY}{user_id}:{design_id}", 1, 5, TimeUnit.MINUTES)
        return result is not None

    async def invalidate_user_purchase_cache(self, user_id: int,design_id: int):
        """
        清除用户购买相关的所有缓存
        
        :param user_id: 用户ID
        """
        # 清楚用户是否有权限的缓存
        await redis_client.get(f"{self.CACHE_KEY}{user_id}:{design_id}")

        # 清除用户购买的设计ID列表缓存（本service管理的缓存）
        cache_key = f"{self.CACHE_KEY}purchased_list:{user_id}"
        await redis_client.delete(cache_key)
        logger.info(f"🗑️ 已清除用户 {user_id} 的购买ID列表缓存")

        # 调用 design_product_service 清除其管理的缓存
        from application.apis.product.design.service.design_product_service import design_product_service
        await design_product_service.invalidate_purchased_cache(user_id)

    async def bind_license(self, user_id: int, sku : SKU, design_license_plan: DesignLicensePlan):
        """
        绑定授权
        """
        is_buyout = design_license_plan.license_type == LicenseType.BUYOUT or design_license_plan.license_type == LicenseType.COMMERCIAL
        logger.error(f"授权类型: {design_license_plan}")
        # 创建用户设计授权记录
        user_design_license = await UserDesignLicense.create(
            user_id=user_id,
            design_id=sku.design_id,
            product_id = sku.product_id,
            design_license_plan_id=design_license_plan.id,
            is_buyout=is_buyout,
            license_type=design_license_plan.license_type
        )

        # 清除用户购买相关的缓存，确保用户能立即看到新购买的作品
        await self.invalidate_user_purchase_cache(user_id,sku.design_id)

        # 如果是买断授权的话,需要更新设计状态和商品状态
        if not is_buyout:
            return user_design_license

        # 获取设计作品信息
        design = await design_service.get_by_id(sku.design_id)
        if not design:
            return user_design_license

        # 将设计的状态设置为买断
        await design_service.change_design_state(
            design_id=sku.design_id,
            user_id=design.user_id,
            new_state=DesignState.BOUGHT_OUT
        )

        # 如果设计关联了商品,将商品设置为下架
        if design.product_id:
            await product_service.update_publish_status(
                product_id=design.product_id,
                is_published=False
            )
        await self.has_license(user_id, sku.design_id)
        return user_design_license

    async def get_user_purchased_design_ids(self, user_id: int) -> list[int]:
        """
        获取用户已购买的所有设计作品ID列表（带缓存）
        
        :param user_id: 用户ID
        :return: 设计作品ID列表
        """
        cache_key = f"{self.CACHE_KEY}purchased_list:{user_id}"
        
        # 尝试从缓存获取
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            logger.debug(f"✅ 从缓存获取用户 {user_id} 的购买列表")
            return cached_data
        
        # 使用分布式锁防止缓存穿透
        lock_key = f"{self.CACHE_KEY}lock:purchased_list:{user_id}"
        async with redis_client.lock(lock_key, expire=5, timeout=3.0):
            # 双重检查缓存
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                logger.debug(f"✅ 从缓存获取用户 {user_id} 的购买列表（锁内二次检查）")
                return cached_data
            
            # 从数据库查询
            licenses = await UserDesignLicense.filter(user_id=user_id).all()
            design_ids = [license.design_id for license in licenses]
            
            # 缓存结果（5分钟）
            await redis_client.set(cache_key, design_ids, 5, TimeUnit.MINUTES)
            logger.debug(f"💾 已缓存用户 {user_id} 的购买列表")
            
            return design_ids


user_design_license_service = UserDesignLicenseService()
