"""
产品与设计作品关联服务
统一管理产品（Product）和设计作品（Design）之间的双向绑定关系
"""
from typing import Optional
from tortoise.transactions import atomic

from application.common.constants import BoolEnum
from application.common.models.product import Product, ProductCheckState, ProductType, SKU
from application.common.models.design import Design
from application.core.redis_client import redis_client
from application.service.design_license_plan_service import design_license_plan_service
from application.service.product_service import product_service
from application.service.design_service import design_service
from application.core.logger_util import logger
from application.service.sku_service import sku_service


class ProductDesignService:
    """
    产品与设计作品关联服务
    负责管理 Product 和 Design 之间的双向绑定关系
    """

    @atomic()
    async def create_product_for_design(self, design: Design, is_official: BoolEnum = BoolEnum.NO) -> Optional[
        Product]:
        """
        为设计作品创建对应的商品和SKU（带分布式锁，防止同一设计作品并发创建）

        :param is_official: 是否为自营商品
        :param design: 设计作品对象
        :return: 创建的商品对象，如果创建失败则返回 None
        """
        # 使用分布式锁确保同一设计作品不会并发创建商品
        lock_key = f"lock:create_for_design:{design.id}"
        async with redis_client.lock(lock_key, expire=30, timeout=10.0):
            try:
                # 检查是否已经为该设计作品创建了商品（通过查询 SKU 的 design_id）
                existing_sku = await SKU.filter(design_id=design.id).first()
                if existing_sku:
                    existing_product = await product_service.get_by_id(existing_sku.product_id)
                    if existing_product:
                        logger.info(f"设计作品 {design.id} 已存在商品 {existing_product.id}，跳过创建")
                        return existing_product

                # 获取所有授权方案
                license_plans = await design_license_plan_service.model_class.all()

                if not license_plans:
                    logger.warning(f"未找到授权方案，无法为设计作品 {design.id} 创建商品")
                    return None

                # 创建商品对象
                product = Product(
                    name=design.title,
                    subtitle=design.description if design.description else None,
                    cover_image=design.images[0] if design.images else "",
                    image_urls=design.images if design.images else [],
                    description=design.description,
                    detail_html=design.detail,
                    category_id=design.category_id or 0,
                    series_id=design.series_id or 0,
                    is_published=False,  # 默认不上架，需要审核通过后才能上架
                    creator_user_id=design.user_id,
                    check_state=ProductCheckState.PENDING,
                    product_type=ProductType.DESIGN,  # 设计作品属于数字商品
                    tags=design.tags if design.tags else [],
                    is_official=is_official
                )

                # 保存商品（使用带锁的创建方法）
                product = await product_service.create(product)
                logger.info(f"✅ 为设计作品 {design.id} 创建商品 {product.id}")

                # 为每个授权方案创建对应的 SKU（使用 sku_service）
                sku_list = []
                for plan in license_plans:
                    sku = SKU(
                        product_id=product.id,
                        name=f"{design.title} - {plan.description or plan.license_type.value}",
                        price=plan.base_price if plan.base_price else 0,
                        original_price=None,
                        stock=-1,  # 数字商品库存设为-1表示无限
                        code=f"DESIGN_{design.id}_{plan.license_type.value}",
                        attributes={
                            "license_type": plan.license_type.value,
                        },
                        is_enabled=True,
                        design_license_plan_id=plan.id,  # 直接使用 design_license_plan_id 字段
                        design_id=design.id,  # 关联设计作品ID
                    )
                    sku_list.append(sku)

                # 批量创建 SKU
                if sku_list:
                    await sku_service.bulk_create(sku_list)
                    logger.info(f"✅ 为商品 {product.id} 创建了 {len(sku_list)} 个 SKU")

                # 更新设计作品的 product_id
                design.product_id = product.id
                await design.save()

                return product

            except Exception as e:
                logger.error(f"❌ 为设计作品 {design.id} 创建商品失败: {str(e)}")
                return None


    @atomic()
    async def delete_design_with_product(self, design_id: int, user_id: int) -> bool:
        """
        删除设计作品及其绑定的商品（双向删除）
        
        Args:
            design_id: 设计作品ID
            user_id: 用户ID（用于权限验证）
            
        Returns:
            是否删除成功
        """
        # 1. 先获取设计作品信息（用于后续删除产品）
        design = await design_service.get_by_id(design_id)
        if not design:
            logger.warning(f"设计作品 {design_id} 不存在，跳过删除")
            return False

        # 2. 删除绑定的商品（如果存在）
        if design.product_id:
            try:
                # 删除商品（会同时删除相关的SKU）
                deleted_count = await product_service.delete_by_id(design.product_id)
                if deleted_count > 0:
                    logger.info(f"🗑️ 删除了设计作品 {design_id} 绑定的商品 {design.product_id}")
            except Exception as e:
                logger.error(f"❌ 删除设计作品 {design_id} 绑定的商品失败: {str(e)}")
                # 继续删除设计作品，不因为商品删除失败而中断

        # 3. 删除设计作品（软删除）
        success = await design_service.delete_design(design_id, user_id)
        
        if success:
            logger.info(f"✅ 成功删除设计作品 {design_id} 及其绑定的商品")
        
        return success

    @atomic()
    async def delete_product_with_design(self, product_id: int) -> bool:
        """
        删除商品及其绑定的设计作品（双向删除）
        
        Args:
            product_id: 商品ID
            
        Returns:
            是否删除成功
        """
        # 1. 先获取商品信息（用于后续删除设计）
        product = await product_service.get_by_id(product_id)
        if not product:
            logger.warning(f"商品 {product_id} 不存在，跳过删除")
            return False

        # 2. 删除绑定的设计作品（如果存在）
        if product.designId:
            try:
                # 获取设计作品的用户ID（用于权限验证，这里使用创建者ID）
                design = await design_service.get_by_id(product.designId)
                if design:
                    # 删除设计作品（软删除）
                    success = await design_service.delete_design(
                        product.designId,
                        design.user_id
                    )
                    if success:
                        logger.info(f"🗑️ 删除了商品 {product_id} 绑定的设计作品 {product.designId}")
                else:
                    logger.warning(f"设计作品 {product.designId} 不存在，跳过删除")
            except Exception as e:
                logger.error(f"❌ 删除商品 {product_id} 绑定的设计作品失败: {str(e)}")
                # 继续删除商品，不因为设计作品删除失败而中断

        # 3. 删除商品（会同时删除相关的SKU）
        deleted_count = await product_service.delete_by_id(product_id)
        
        if deleted_count > 0:
            logger.info(f"✅ 成功删除商品 {product_id} 及其绑定的设计作品")
        
        return deleted_count > 0

    async def sync_design_to_product(self, design: Design) -> Optional[Product]:
        """
        同步设计作品信息到绑定的商品（更新商品信息）
        
        Args:
            design: 设计作品对象
            
        Returns:
            更新后的商品对象，如果不存在绑定则返回 None
        """
        if not design.product_id:
            return None

        product = await product_service.get_by_id(design.product_id)
        if not product:
            logger.warning(f"商品 {design.product_id} 不存在，无法同步")
            return None

        # 同步设计作品信息到商品
        update_data = {
            "name": design.title,
            "subtitle": design.description if design.description else None,
            "cover_image": design.images[0] if design.images else "",
            "image_urls": design.images if design.images else [],
            "description": design.description,
            "detail_html": design.detail,
            "category_id": design.category_id or 0,
            "series_id": design.series_id or 0,
            "tags": design.tags if design.tags else [],
        }

        # 更新商品
        await product_service.update_by_id(product.id, update_data)
        logger.info(f"✅ 同步设计作品 {design.id} 信息到商品 {product.id}")

        # 重新获取更新后的商品
        return await product_service.get_by_id(product.id)

    async def sync_product_to_design(self, product: Product) -> Optional[Design]:
        """
        同步商品信息到绑定的设计作品（更新设计作品信息）
        
        Args:
            product: 商品对象
            
        Returns:
            更新后的设计作品对象，如果不存在绑定则返回 None
        """
        # 从 SKU 中获取 design_id
        skus = await SKU.filter(product_id=product.id).first()
        if not skus or not skus.design_id:
            return None

        design = await design_service.get_by_id(skus.design_id)
        if not design:
            logger.warning(f"设计作品 {skus.design_id} 不存在，无法同步")
            return None

        # 同步商品信息到设计作品
        design.title = product.name
        design.description = product.description
        design.detail = product.detail_html
        design.category_id = product.category_id if product.category_id else None
        design.series_id = product.series_id if product.series_id else None
        design.tags = product.tags if product.tags else []
        design.images = product.image_urls if product.image_urls else []

        # 更新设计作品
        design = await design_service.update_design(design, design.user_id)
        logger.info(f"✅ 同步商品 {product.id} 信息到设计作品 {design.id}")

        return design


# 创建全局实例
product_design_service = ProductDesignService()

