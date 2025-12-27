from datetime import datetime
from application.service.product_service import product_service
from application.common.models.product import Product, SKU, ProductType, ProductCheckState
from application.common.models.vip import VIPPlan
from application.common.constants.BoolEnum import BoolEnum
from application.core.redis_client import redis_client, TimeUnit
from application.core.logger_util import logger


class VipProductService:
    """
    VIP产品服务（用户端）
    支持VIP产品列表查询，带Redis缓存优化
    用户端不接受查询参数，直接返回全部已审核通过且已上架的VIP商品
    """
    
    # Redis 缓存键
    CACHE_KEY = "vip_product:list:default"
    
    # 缓存过期时间（默认30分钟）
    CACHE_EXPIRE = 30
    CACHE_UNIT = TimeUnit.MINUTES
    
    async def invalidate_all_cache(self):
        """
        删除VIP产品列表缓存
        用户端只有一个固定的缓存键
        """
        try:
            deleted = await redis_client.delete(self.CACHE_KEY)
            if deleted:
                logger.info(f"✅ 已删除VIP产品列表缓存: {self.CACHE_KEY}")
        except Exception as e:
            logger.error(f"❌ 删除VIP产品列表缓存失败: {e}")
    
    async def query_vip_product_list(self):
        """
        查询VIP套餐商品列表（用户端）
        只返回已审核通过且已上架的VIP商品（不分页）
        不接受查询参数，直接查询全部数据并缓存
        """
        # 🔧 临时禁用缓存，用于测试新的数据结构
        # TODO: 测试完成后可以恢复缓存逻辑
        # 尝试从缓存获取
        # cached_data = await redis_client.get(self.CACHE_KEY)
        # if cached_data:
        #     logger.debug(f"✅ 从缓存获取VIP产品列表: {self.CACHE_KEY}")
        #     return cached_data
        
        logger.debug(f"💾 直接查询数据库（缓存已禁用）: {self.CACHE_KEY}")
        
        # 构建查询条件：只查询已审核通过、已上架、未删除的VIP商品
        # 用户端不接受keyword，直接查询全部
        query = Product.filter(
            product_type=ProductType.VIP,
            check_state=ProductCheckState.APPROVED,
            is_published=True,
            is_deleted=BoolEnum.NO
        )
        
        # 查询所有符合条件的商品（不分页）
        select_fields = [
            "id", "name", "subtitle", "description",
            "is_published", "sort", "created_at", "updated_at"
        ]
        
        # 使用 values 方法直接获取字典列表
        products = await query.order_by("-sort", "-created_at").values(*select_fields)
        
        # 转换为列表，并处理 datetime 对象
        items = []
        for product in products:
            item = dict(product)
            # 将 datetime 对象转换为字符串
            for key, value in item.items():
                if isinstance(value, datetime):
                    item[key] = value.isoformat()
            # 添加 productId 字段（与 id 相同，方便前端使用）
            item["product_id"] = item["id"]
            items.append(item)
        
        # 关联查询 VIP 套餐信息
        if not items:
            # 即使为空也缓存，避免频繁查询数据库
            await redis_client.set(
                self.CACHE_KEY,
                items,
                time=self.CACHE_EXPIRE,
                unit=self.CACHE_UNIT
            )
            return items

        # 获取商品ID列表
        product_ids = [item["id"] for item in items]
        
        # 批量查询 SKU 信息（查询更多字段，包括价格信息）
        skus = await SKU.filter(product_id__in=product_ids).order_by("id").values(
            "id", "product_id", "name", "price", "original_price", "vip_plan_id"
        )
        
        # 构建 product_id -> sku 的映射（每个商品取第一个 SKU）
        product_sku_map = {}
        product_vip_map = {}
        vip_plan_ids = set()
        
        for sku in skus:
            product_id = sku["product_id"]
            # 如果该商品还没有记录 SKU，则记录第一个
            if product_id not in product_sku_map:
                product_sku_map[product_id] = {
                    "sku_id": sku["id"],
                    "sku_name": sku["name"],
                    "price": sku["price"],
                    "original_price": sku["original_price"]
                }
            
            # 构建 vip_plan_id 映射
            if sku.get("vip_plan_id"):
                product_vip_map[product_id] = sku["vip_plan_id"]
                vip_plan_ids.add(sku["vip_plan_id"])
        
        if not vip_plan_ids:
            # 没有关联套餐，统一补 None
            for item in items:
                item["vip_plan_id"] = None
                item["vip_plan"] = None
                # 将 SKU 信息展开到商品中
                sku_info = product_sku_map.get(item["id"], {})
                item["sku_id"] = sku_info.get("sku_id")
                item["sku_name"] = sku_info.get("sku_name")
                item["price"] = sku_info.get("price")
                item["original_price"] = sku_info.get("original_price")
            # 缓存结果
            await redis_client.set(
                self.CACHE_KEY,
                items,
                time=self.CACHE_EXPIRE,
                unit=self.CACHE_UNIT
            )
            return items

        # 批量查询 VIP 套餐
        vip_plans = await VIPPlan.filter(id__in=vip_plan_ids)
        vip_plan_map = {}
        for plan in vip_plans:
            plan_dict = plan.to_dict()
            # 处理 VIPPlan 中的 datetime 对象
            for key, value in plan_dict.items():
                if isinstance(value, datetime):
                    plan_dict[key] = value.isoformat()
            vip_plan_map[plan.id] = plan_dict

        # 关联套餐信息和 SKU 信息到商品列表
        for item in items:
            vip_plan_id = product_vip_map.get(item["id"])
            item["vip_plan_id"] = vip_plan_id
            item["vip_plan"] = vip_plan_map.get(vip_plan_id)
            # 将 SKU 信息展开到商品中（VIP 商品只有一个 SKU，取第一个）
            sku_info = product_sku_map.get(item["id"], {})
            item["sku_id"] = sku_info.get("sku_id")
            item["sku_name"] = sku_info.get("sku_name")
            item["price"] = sku_info.get("price")
            item["original_price"] = sku_info.get("original_price")

        # 保存到缓存
        await redis_client.set(
            self.CACHE_KEY,
            items,
            time=self.CACHE_EXPIRE,
            unit=self.CACHE_UNIT
        )
        logger.debug(f"💾 已缓存VIP产品列表: {self.CACHE_KEY}")

        return items


vip_product_service = VipProductService()

