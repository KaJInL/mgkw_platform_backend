from typing import Optional, List, Dict, Any

from tortoise.transactions import atomic

from application.common.base import BaseService
from application.common.models import Product, SKU
from application.common.models.design import Design, DesignState
from application.common.models.product import ProductType, ProductCheckState
from application.common.constants.BoolEnum import BoolEnum
from application.common.schema.product_schema import ProductWithSkusInfo, SkuInfo
from application.service.design_license_plan_service import design_license_plan_service
from application.service.sku_service import sku_service
from application.core.redis_client import redis_client, TimeUnit
from application.core.logger_util import logger


class ProductService(BaseService[Product]):
    """产品service"""

    # Redis 缓存键前缀
    CACHE_PREFIX = "product_bk"
    CACHE_ITEM_KEY = f"{CACHE_PREFIX}:item"
    CACHE_WITH_SKUS_KEY = f"{CACHE_PREFIX}:with_skus"

    # 缓存过期时间（默认30分钟）
    CACHE_EXPIRE = 30
    CACHE_UNIT = TimeUnit.MINUTES

    async def get_by_id(self, product_id: int, select_fields: Optional[List[str]] = None) -> Optional[Product]:
        """
        根据ID获取商品（带缓存和分布式锁，防止缓存穿透）
        
        :param product_id: 商品ID
        :param select_fields: 查询的字段
        :return: 商品对象
        """
        cache_key = f"{self.CACHE_ITEM_KEY}:{product_id}"

        # 尝试从缓存获取
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            logger.debug(f"✅ 从缓存获取商品 {product_id}")
            return self.dict_to_model(cached_data)

        # 使用分布式锁防止缓存穿透（多个并发请求同时查询数据库）
        lock_key = f"{self.CACHE_PREFIX}:lock:get:{product_id}"
        async with redis_client.lock(lock_key, expire=5, timeout=3.0):
            # 再次检查缓存（双重检查，防止在等待锁期间其他请求已写入缓存）
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                logger.debug(f"✅ 从缓存获取商品 {product_id}（锁内二次检查）")
                return self.dict_to_model(cached_data)

            # 从数据库查询（调用父类方法，避免递归）
            product = await super().get_by_id(product_id, select_fields)
            if not product:
                return None

            # 保存到缓存
            await redis_client.set(
                cache_key,
                product.to_dict(),
                time=self.CACHE_EXPIRE,
                unit=self.CACHE_UNIT
            )
            logger.debug(f"💾 已缓存商品 {product_id}")

            return product

    async def get_by_id_with_skus(self, product_id: int) -> Optional[ProductWithSkusInfo]:
        """
        根据ID获取商品（包含SKU列表，带缓存和分布式锁，防止缓存穿透）
        
        :param product_id: 商品ID
        :return: 商品信息（包含SKU列表）
        """
        cache_key = f"{self.CACHE_WITH_SKUS_KEY}:{product_id}"

        # 尝试从缓存获取
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            logger.debug(f"✅ 从缓存获取商品（含SKU） {product_id}")
            return ProductWithSkusInfo(**cached_data)

        # 使用分布式锁防止缓存穿透（多个并发请求同时查询数据库和SKU）
        lock_key = f"{self.CACHE_PREFIX}:lock:get_with_skus:{product_id}"
        async with redis_client.lock(lock_key, expire=5, timeout=3.0):
            # 再次检查缓存（双重检查，防止在等待锁期间其他请求已写入缓存）
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                logger.debug(f"✅ 从缓存获取商品（含SKU） {product_id}（锁内二次检查）")
                return ProductWithSkusInfo(**cached_data)

            # 从数据库查询商品
            product = await self.get_by_id(product_id)
            if not product:
                return None

            # 查询SKU列表
            skus = await sku_service.get_skus_by_product_id(product_id)

            # 构建返回对象
            product_dict = product.to_dict()
            product_dict["skus"] = [sku.to_dict() for sku in skus]
            product_with_skus = ProductWithSkusInfo(**product_dict)

            # 保存到缓存
            await redis_client.set(
                cache_key,
                product_with_skus.model_dump(),
                time=self.CACHE_EXPIRE,
                unit=self.CACHE_UNIT
            )
            logger.debug(f"💾 已缓存商品（含SKU） {product_id}")

            return product_with_skus

    async def invalidate_cache(self, product_id: Optional[int] = None):
        """
        清除商品相关缓存
        
        :param product_id: 商品ID（可选）
        """
        if product_id:
            # 清除单个商品缓存
            cache_key = f"{self.CACHE_ITEM_KEY}:{product_id}"
            await redis_client.delete(cache_key)
            # 清除带SKU的缓存
            cache_key_with_skus = f"{self.CACHE_WITH_SKUS_KEY}:{product_id}"
            await redis_client.delete(cache_key_with_skus)
            logger.debug(f"🗑️ 已清除商品 {product_id} 的缓存")

    async def create(self, product: Product) -> Product:
        """
        创建商品（带分布式锁）
        
        :param product: 商品对象
        :return: 创建的商品对象
        """
        # 如果是自营商品，默认审核通过并上架
        if BoolEnum.is_yes(product.is_official):
            product.check_state = ProductCheckState.APPROVED
            product.is_published = True

        # 使用分布式锁确保创建操作的线程安全
        lock_key = f"{self.CACHE_PREFIX}:lock:create"
        async with redis_client.lock(lock_key, expire=10, timeout=5.0):
            # 保存商品
            await product.save()
            logger.info(f"✅ 创建商品 {product.id}")

            # 清除相关缓存
            await self.invalidate_cache(product_id=product.id)

            return product

    async def update_by_id(self, product_id: int, data: Dict[str, Any], is_official: BoolEnum = BoolEnum.NO) -> int:
        """
        根据ID更新商品（带分布式锁和缓存清除）
        
        :param is_official: 是否为自营商品
        :param product_id: 商品ID
        :param data: 更新数据
        :return: 更新的记录数
        """
        # 如果是自营商品，默认审核通过并上架
        if isinstance(data, dict):
            if "is_self_operated" in data and BoolEnum.is_yes(data["is_self_operated"]):
                data["check_state"] = ProductCheckState.APPROVED.value
                data["is_published"] = True

        if BoolEnum.is_yes(is_official):
            data.check_state = ProductCheckState.APPROVED
            data.is_published = True

        # 使用分布式锁确保同一商品的更新操作串行执行
        try:
            lock_key = f"{self.CACHE_PREFIX}:lock:update:{product_id}"
            async with redis_client.lock(lock_key, expire=10, timeout=5.0):
                # 更新商品
                updated_count = await super().update_by_id(product_id, data)

                if updated_count > 0:
                    # 清除缓存
                    await self.invalidate_cache(product_id=product_id)
                    logger.info(f"✅ 更新商品 {product_id}")

                return updated_count
        except Exception as e:
            logger.error(f"❌ 更新商品 {product_id} 失败：{e}")
            raise e

    async def delete_by_id(self, product_id: int) -> int:
        """
        根据ID删除商品（带分布式锁，同时删除相关SKU）
        
        :param product_id: 商品ID
        :return: 删除的记录数
        """
        # 使用分布式锁确保同一商品的删除操作串行执行
        lock_key = f"{self.CACHE_PREFIX}:lock:delete:{product_id}"
        async with redis_client.lock(lock_key, expire=10, timeout=5.0):
            # 先删除相关的SKU
            sku_count = await sku_service.delete_skus_by_product_id(product_id)
            logger.info(f"🗑️ 删除了 {sku_count} 个 SKU（商品 {product_id}）")

            # 删除商品
            deleted_count = await super().delete_by_id(product_id)

            if deleted_count > 0:
                # 清除缓存
                await self.invalidate_cache(product_id=product_id)
                logger.info(f"🗑️ 删除商品 {product_id}")

            return deleted_count

    async def update_publish_status(self, product_id: int, is_published: bool) -> bool:
        """
        更新商品上下架状态（带分布式锁和缓存清除）
        
        :param product_id: 商品ID
        :param is_published: 是否上架（True=上架，False=下架）
        :return: 是否更新成功
        """
        # 使用分布式锁确保同一商品的更新操作串行执行
        lock_key = f"{self.CACHE_PREFIX}:lock:publish:{product_id}"
        try:
            async with redis_client.lock(lock_key, expire=10, timeout=5.0):
                # 更新商品上架状态
                updated_count = await super().update_by_id(product_id, {"is_published": is_published})
                
                if updated_count > 0:
                    # 清除缓存
                    await self.invalidate_cache(product_id=product_id)
                    status_text = "上架" if is_published else "下架"
                    logger.info(f"✅ 商品 {product_id} 已{status_text}")
                    return True
                else:
                    logger.warning(f"⚠️ 商品 {product_id} 更新失败，可能不存在")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ 更新商品 {product_id} 上架状态失败：{e}")
            raise e

    async def delete_product_by_design_id(self, design_id: int) -> bool:
        """
        根据设计作品ID删除对应的商品和SKU（带分布式锁，防止并发删除）
        
        :param design_id: 设计作品ID
        :return: 是否删除成功
        """
        # 使用分布式锁确保同一设计作品的删除操作串行执行
        lock_key = f"{self.CACHE_PREFIX}:lock:delete_by_design:{design_id}"
        async with redis_client.lock(lock_key, expire=30, timeout=10.0):
            try:
                # 从 SKU 中查询 design_id 对应的所有商品ID
                from application.common.models.product import SKU
                skus = await SKU.filter(design_id=design_id).all()

                if not skus:
                    logger.info(f"未找到设计作品 {design_id} 对应的商品")
                    return True  # 没有找到商品也算成功（可能之前没有创建商品）

                # 获取所有商品ID（去重）
                product_ids = list(set([sku.product_id for sku in skus]))

                # 删除所有相关的 SKU（使用 sku_service）
                sku_count = await sku_service.delete_skus_by_product_ids(product_ids)
                logger.info(f"🗑️ 删除了 {sku_count} 个 SKU（设计作品 {design_id}）")

                # 删除所有相关的商品（每个商品删除都有锁保护）
                for product_id in product_ids:
                    await self.delete_by_id(product_id)

                logger.info(f"🗑️ 删除了 {len(product_ids)} 个商品（设计作品 {design_id}）")

                return True

            except Exception as e:
                logger.error(f"❌ 删除设计作品 {design_id} 对应的商品失败: {str(e)}")
                return False


product_service = ProductService()
