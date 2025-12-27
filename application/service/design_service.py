from typing import Optional, List, Dict, Any
from datetime import datetime
from tortoise.queryset import QuerySet
from application.common.base.base_service import BaseService
from application.common.models.design import Design, DesignState
from application.common.constants import BoolEnum
from application.core.redis_client import redis_client, TimeUnit
from application.core.logger_util import logger


class DesignService(BaseService[Design]):
    """
    设计作品服务
    支持设计师上传和管理自己的作品，带 Redis 缓存优化
    """

    # Redis 缓存键前缀
    CACHE_PREFIX = "design"
    CACHE_ITEM_KEY = f"{CACHE_PREFIX}:item"
    CACHE_USER_DESIGNS_KEY = f"{CACHE_PREFIX}:user"

    # 缓存过期时间（默认30分钟）
    CACHE_EXPIRE = 30
    CACHE_UNIT = TimeUnit.MINUTES

    async def get_by_id_with_cache(
        self, 
        design_id: int, 
        include_deleted: bool = False
    ) -> Optional[Design]:
        """
        根据ID获取设计作品（带缓存）
        
        :param design_id: 设计作品ID
        :param include_deleted: 是否包含已删除的作品（用于已购买用户访问）
        :return: 设计作品对象
        """
        cache_key = f"{self.CACHE_ITEM_KEY}:{design_id}"
        if include_deleted:
            cache_key += ":with_deleted"

        # 尝试从缓存获取
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            logger.debug(f"✅ 从缓存获取设计作品 {design_id}")
            # 将缓存的字典转换为模型对象
            return self.dict_to_model(cached_data)

        # 从数据库查询
        if include_deleted:
            design = await self.get_by_id(design_id)
        else:
            design = await self.get_one(id=design_id, is_deleted=BoolEnum.NO)
        
        if not design:
            return None

        # 保存到缓存（存储字典格式）
        await redis_client.set(
            cache_key,
            design.to_dict(),
            time=self.CACHE_EXPIRE,
            unit=self.CACHE_UNIT
        )
        logger.debug(f"💾 已缓存设计作品 {design_id}")

        return design

    async def get_user_designs_with_cache(
        self,
        user_id: int,
        state: Optional[DesignState] = None,
        include_deleted: bool = False
    ) -> List[Design]:
        """
        获取用户的设计作品列表（带缓存）
        
        :param user_id: 用户ID
        :param state: 作品状态过滤
        :param include_deleted: 是否包含已删除的作品
        :return: 设计作品对象列表
        """
        cache_key = f"{self.CACHE_USER_DESIGNS_KEY}:{user_id}"
        if state:
            cache_key += f":{state.value}"
        if include_deleted:
            cache_key += ":with_deleted"

        # 尝试从缓存获取
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            logger.debug(f"✅ 从缓存获取用户 {user_id} 的作品列表")
            # 将缓存的字典列表转换为模型对象列表
            return [self.dict_to_model(item) for item in cached_data]

        # 从数据库查询
        filters = {"user_id": user_id}
        if state:
            filters["state"] = state
        
        # 默认不包含已删除的
        if not include_deleted:
            filters["is_deleted"] = BoolEnum.NO

        # 从数据库查询
        designs = await self.list(filters=filters, order_by=["-created_at"])

        # 转换为字典并保存到缓存
        if designs:
            designs_dict = [d.to_dict() for d in designs]
            await redis_client.set(
                cache_key,
                designs_dict,
                time=self.CACHE_EXPIRE,
                unit=self.CACHE_UNIT
            )
            logger.debug(f"💾 已缓存用户 {user_id} 的作品列表")
            return designs_dict

        return []

    async def search_designs(
        self,
        keyword: Optional[str] = None,
        category_id: Optional[int] = None,
        series_id: Optional[int] = None,
        state: Optional[DesignState] = None,
        is_official: Optional[bool] = None,
        tags: Optional[List[str]] = None,
        include_deleted: bool = False
    ) -> QuerySet:
        """
        搜索设计作品（返回 QuerySet 用于分页）
        
        :param keyword: 搜索关键词（标题、描述）
        :param category_id: 分类ID
        :param series_id: 系列ID
        :param state: 作品状态
        :param is_official: 是否官方作品
        :param tags: 标签列表
        :param include_deleted: 是否包含已删除的作品
        :return: QuerySet 对象
        """
        query = Design.all()
        
        # 默认不包含已删除的作品
        if not include_deleted:
            query = query.filter(is_deleted=BoolEnum.NO)

        # 关键词搜索
        if keyword:
            query = query.filter(title__icontains=keyword) | query.filter(description__icontains=keyword)

        # 分类筛选
        if category_id is not None:
            query = query.filter(category_id=category_id)

        # 系列筛选
        if series_id is not None:
            query = query.filter(series_id=series_id)

        # 状态筛选
        if state is not None:
            query = query.filter(state=state)

        # 官方筛选
        if is_official is not None:
            query = query.filter(is_official=BoolEnum.YES if is_official else BoolEnum.NO)

        # 标签筛选（包含任意一个标签）
        if tags:
            # JSON 字段的查询需要特殊处理
            for tag in tags:
                query = query.filter(tags__contains=tag)

        return query

    async def invalidate_cache(self, design_id: int, user_id: Optional[int] = None):
        """
        清除设计作品相关缓存
        
        :param design_id: 设计作品ID
        :param user_id: 用户ID（可选，如果提供则清除用户作品列表缓存）
        """
        # 清除作品详情缓存
        cache_key = f"{self.CACHE_ITEM_KEY}:{design_id}"
        await redis_client.delete(cache_key)
        logger.debug(f"🗑️ 已清除设计作品 {design_id} 的缓存")

        # 清除用户作品列表缓存
        if user_id:
            # 清除所有状态的缓存
            for state in DesignState:
                cache_key = f"{self.CACHE_USER_DESIGNS_KEY}:{user_id}:{state.value}"
                await redis_client.delete(cache_key)
            # 清除无状态筛选的缓存
            cache_key = f"{self.CACHE_USER_DESIGNS_KEY}:{user_id}"
            await redis_client.delete(cache_key)
            logger.debug(f"🗑️ 已清除用户 {user_id} 的作品列表缓存")

    async def create_design(self, user_id: int, design: Design) -> Design:
        """
        创建设计作品
        
        :param user_id: 用户ID
        :param design: 作品对象（已设置好属性）
        :return: 创建的作品对象
        """
        design.user_id = user_id
        await design.save()
        
        # 清除用户作品列表缓存
        await self.invalidate_cache(design.id, user_id)
        
        return design

    async def update_design(
        self,
        design: Design,
        user_id: int
    ) -> Optional[Design]:
        """
        更新设计作品（只能更新自己的作品）
        
        :param design: 要更新的作品对象（包含新数据）
        :param user_id: 用户ID
        :return: 更新后的作品对象
        """
        # 验证作品归属
        existing = await self.get_one(id=design.id, user_id=user_id)
        if not existing:
            return None

        # 更新作品
        await design.save()
        
        # 清除缓存
        await self.invalidate_cache(design.id, user_id)
        
        return design

    async def delete_design(self, design_id: int, user_id: int) -> bool:
        """
        软删除设计作品（只能删除自己的作品）
        已购买的用户仍然可以通过特定接口访问
        
        :param design_id: 作品ID
        :param user_id: 用户ID
        :return: 是否删除成功
        """
        # 验证作品归属
        design = await self.get_one(id=design_id, user_id=user_id)
        if not design:
            return False

        # 软删除：标记为已删除
        design.is_deleted = BoolEnum.YES
        design.deleted_at = datetime.now()
        await design.save()
        
        # 清除缓存
        await self.invalidate_cache(design_id, user_id)
        logger.info(f"🗑️ 作品 {design_id} 已软删除，购买用户仍可访问")
        return True

    async def change_design_state(
        self,
        design_id: int,
        user_id: int,
        new_state: DesignState
    ) -> Optional[Design]:
        """
        修改作品状态（只能修改自己的作品）
        
        :param design_id: 作品ID
        :param user_id: 用户ID
        :param new_state: 新状态
        :return: 更新后的作品对象
        """
        # 获取作品并验证归属
        design = await self.get_one(id=design_id, user_id=user_id)
        if not design:
            return None
        
        # 更新状态
        design.state = new_state
        await design.save()
        
        # 清除缓存
        await self.invalidate_cache(design_id, user_id)
        
        return design

    async def get_design_for_buyer(self, design_id: int) -> Optional[Design]:
        """
        为购买者获取作品详情（即使作品已被作者删除）
        此方法应该在订单系统中使用，确保购买者能看到已购买的作品
        
        :param design_id: 作品ID
        :return: 作品对象（包含已删除的）
        """
        return await self.get_by_id(design_id)

    async def restore_design(self, design_id: int, user_id: int) -> bool:
        """
        恢复已软删除的作品
        
        :param design_id: 作品ID
        :param user_id: 用户ID
        :return: 是否恢复成功
        """
        # 验证作品归属和删除状态
        design = await self.get_one(
            id=design_id, 
            user_id=user_id,
            is_deleted=BoolEnum.YES
        )
        
        if not design:
            return False

        # 恢复作品
        design.is_deleted = BoolEnum.NO
        design.deleted_at = None
        await design.save()
        
        # 清除缓存
        await self.invalidate_cache(design_id, user_id)
        logger.info(f"♻️ 作品 {design_id} 已恢复")
        return True


# 创建全局实例
design_service = DesignService()

