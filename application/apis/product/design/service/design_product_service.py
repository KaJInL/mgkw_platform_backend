from typing import List, Dict, Any
from application.service.design_service import design_service
from application.service.product_service import product_service
from application.service.design_access_service import design_access_service
from application.service.user_design_license_service import user_design_license_service
from application.common.models.design import Design, DesignState
from application.common.models import SKU
from application.common.constants import BoolEnum
from application.apis.product.schema.request import QueryDesignProductListReq, GetDesignProductDetailReq
from application.core.logger_util import logger
from application.core.redis_client import redis_client, TimeUnit


class DesignProductService:
    # 缓存键前缀
    CACHE_PREFIX = "purchased_design_products"
    
    async def invalidate_purchased_cache(self, user_id: int):
        """
        清除用户已购买设计作品列表的缓存
        
        :param user_id: 用户ID
        """
        cache_key = f"{self.CACHE_PREFIX}:{user_id}"
        await redis_client.delete(cache_key)
        logger.info(f"🗑️ 已清除用户 {user_id} 的已购作品列表缓存")
    
    async def query_design_product_list(self, req: QueryDesignProductListReq):
        """
        前端查询设计作品商品列表
        只返回已通过审核且未删除的设计作品
        """
        # 前端接口只查询已通过审核的设计作品
        query = Design.filter(
            is_deleted=BoolEnum.NO,
            state=DesignState.APPROVED
        )

        if req.keyword:
            query = query.filter(title__icontains=req.keyword)

        # 调用 base_service 的分页方法
        select_fields = [
            "id", "title", "description", "category_id", "series_id",
            "product_id", "tags", "images", "state", "is_official", "is_deleted"
        ]

        return await design_service.paginate_dic(
            query=query,
            page_no=req.page,
            page_size=req.pageSize,
            select_fields=select_fields,
            order_by=["-created_at"]
        )

    async def get_design_product_detail(self, req: GetDesignProductDetailReq):
        """
        前端获取设计作品商品详情
        只返回已通过审核且未删除的设计作品
        
        权限判断逻辑（通过 design_access_service.has_access 判断）：
        1. 如果是作品的创建者，有权限查看完整详情
        2. 如果用户是VIP或管理员，有权限查看完整详情
        3. 如果用户购买了该设计的授权，有权限查看完整详情
        4. 否则没有权限，resource_url和detail会被清空
        """
        # 1. 获取 Design 详情（只返回已审核通过的）
        design_info = await design_service.get_by_id_with_cache(
            design_id=req.design_id,
            include_deleted=False
        )

        # 检查设计作品是否存在且已通过审核
        if not design_info or design_info.state != DesignState.APPROVED:
            logger.warning(f"设计作品 {req.design_id} 不存在或未通过审核")
            raise ValueError("设计作品不存在或未通过审核")

        product_info = None
        if design_info.product_id:
            # 2. 获取 Product 详情 (包含SKU)
            product_info = await product_service.get_by_id_with_skus(
                product_id=design_info.product_id
            )

        # 3. 检查是否有权限查看设计详情（resource_url和detail）
        has_permission = await design_access_service.has_access(design_info)

        # 4. 构建返回数据
        design_dict = design_info.to_dict() if design_info else None

        # 记录原始字段是否存在（用于前端判断是否显示组件）
        has_resource_url = bool(design_info.resource_url) if design_info else False
        has_detail = bool(design_info.detail) if design_info else False

        # 如果没有权限，清空 resource_url 和 detail（但保留标记）
        if not has_permission and design_dict:
            design_dict["resource_url"] = None
            design_dict["detail"] = None

        # 添加字段存在标记（使用不带下划线的字段名，会被转换为 camelCase）
        if design_dict:
            design_dict["has_resource_url"] = has_resource_url
            design_dict["has_detail"] = has_detail

        return {
            "has_permission": has_permission,
            "design": design_dict,
            "product": product_info.model_dump() if product_info else None
        }

    async def get_purchased_design_products(self, user_id: int) -> List[Dict[str, Any]]:
        """
        获取用户已购买的所有设计作品商品列表
        
        :param user_id: 用户ID
        :return: 商品列表 [{img_url: "", name: "", product_id: ""}]
        """
        # 1. 从缓存获取完整结果
        cache_key = f"{self.CACHE_PREFIX}:{user_id}"
        cached_result = await redis_client.get(cache_key)
        if cached_result:
            logger.debug(f"✅ 从缓存获取用户 {user_id} 的已购作品列表")
            return cached_result

        # 3. 获取用户已购买的所有设计作品ID列表
        design_ids = await user_design_license_service.get_user_purchased_design_ids(user_id)

        if not design_ids:
            # 如果没有购买记录，缓存空列表（30秒）
            await redis_client.set(cache_key, [], 30, TimeUnit.SECONDS)
            return []

        # 4. 通过 design_id 查询对应的 SKU，获取 product_id
        skus = await SKU.filter(design_id__in=design_ids).all()

        if not skus:
            # 如果没有找到对应的SKU，缓存空列表（1分钟）
            await redis_client.set(cache_key, [], 1, TimeUnit.MINUTES)
            return []

        # 5. 获取所有唯一的 product_id
        product_ids = list(set([sku.product_id for sku in skus]))

        # 6. 批量查询商品信息（使用 mget 优化）
        # 先尝试从缓存批量获取
        cache_keys = [f"product_bk:item:{pid}" for pid in product_ids]
        cached_products = await redis_client.mget(cache_keys)

        # 7. 处理缓存结果，找出未命中的 product_id
        products = []
        missing_product_ids = []

        for i, cached_product in enumerate(cached_products):
            if cached_product:
                products.append(cached_product)
            else:
                missing_product_ids.append(product_ids[i])

        # 8. 查询缓存未命中的商品
        if missing_product_ids:
            for product_id in missing_product_ids:
                product = await product_service.get_by_id(product_id)
                if product:
                    products.append(product.to_dict())

        # 9. 构建返回结果
        result = []
        for product_data in products:
            # 兼容 dict 和 Product 对象
            if isinstance(product_data, dict):
                img_url = product_data.get("cover_image")
                name = product_data.get("name")
                product_id = product_data.get("id")
            else:
                img_url = product_data.cover_image
                name = product_data.name
                product_id = product_data.id

            result.append({
                "img_url": img_url,
                "name": name,
                "product_id": product_id
            })

        # 10. 缓存结果（5分钟）
        await redis_client.set(cache_key, result, 5, TimeUnit.MINUTES)
        logger.debug(f"💾 已缓存用户 {user_id} 的已购作品列表")

        return result


design_product_service = DesignProductService()
