from itertools import product

from application.common.base import BaseService
from application.common.models import UserDesignLicense, DesignLicensePlan, LicenseType
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

    async def bind_license(self, user_id: int, design_id: int, design_license_plan: DesignLicensePlan):
        """
        绑定授权
        """
        is_buyout = design_license_plan.license_type == LicenseType.BUYOUT or design_license_plan.license_type == LicenseType.COMMERCIAL
        logger.error(f"授权类型: {design_license_plan}")
        # 创建用户设计授权记录
        user_design_license = await UserDesignLicense.create(
            user_id=user_id,
            design_id=design_id,
            design_license_plan_id=design_license_plan.id,
            is_buyout=is_buyout,
            license_type=design_license_plan.license_type
        )

        # 如果是买断授权的话,需要更新设计状态和商品状态
        if not is_buyout:
            return

        # 获取设计作品信息
        design = await design_service.get_by_id(design_id)
        if not design:
            return

        # 将设计的状态设置为买断
        await design_service.change_design_state(
            design_id=design_id,
            user_id=design.user_id,
            new_state=DesignState.BOUGHT_OUT
        )

        # 如果设计关联了商品,将商品设置为下架
        if design.product_id:
            await product_service.update_publish_status(
                product_id=design.product_id,
                is_published=False
            )
        await self.has_license(user_id, design_id)
        return user_design_license


user_design_license_service = UserDesignLicenseService()
