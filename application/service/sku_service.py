from typing import List, Optional
from application.common.base import BaseService
from application.common.models import SKU


class SkuService(BaseService[SKU]):
    """SKU服务"""

    async def get_skus_by_product_id(self, product_id: int) -> List[SKU]:
        """
        根据商品ID获取所有SKU
        
        :param product_id: 商品ID
        :return: SKU列表
        """
        return await self.model_class.filter(product_id=product_id, is_enabled=True).all()

    async def get_skus_by_product_ids(self, product_ids: List[int]) -> List[SKU]:
        """
        根据多个商品ID批量获取SKU
        
        :param product_ids: 商品ID列表
        :return: SKU列表
        """
        if not product_ids:
            return []
        return await self.model_class.filter(product_id__in=product_ids, is_enabled=True).all()

    async def delete_skus_by_product_id(self, product_id: int) -> int:
        """
        根据商品ID删除所有SKU
        
        :param product_id: 商品ID
        :return: 删除的SKU数量
        """
        return await self.model_class.filter(product_id=product_id).delete()

    async def delete_skus_by_product_ids(self, product_ids: List[int]) -> int:
        """
        根据多个商品ID批量删除SKU
        
        :param product_ids: 商品ID列表
        :return: 删除的SKU数量
        """
        if not product_ids:
            return 0
        return await self.model_class.filter(product_id__in=product_ids).delete()


sku_service = SkuService()
