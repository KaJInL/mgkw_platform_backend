from tortoise.transactions import atomic
from application.apis.product.schema.request import (
    QueryVipProductListReq, CreateVipProductReq, UpdateVipProductReq
)
from application.service.vip_plan_service import vip_plan_service
from application.service.product_service import product_service
from application.service.sku_service import sku_service
from application.apis.product.vip.service.vip_product_service import vip_product_service
from application.common.models.vip import VIPPlan
from application.common.models.product import Product, SKU, ProductType, ProductCheckState
from application.common.constants.BoolEnum import BoolEnum
from application.core.logger_util import logger


class VipProductAdminService:
    """
    VIP产品管理服务
    管理后台专用，直接查询数据库，不使用缓存
    """
    
    async def query_vip_product_list(self, req: QueryVipProductListReq):
        """
        查询VIP套餐商品列表（管理后台）
        直接查询数据库，不使用缓存
        支持关键词搜索和状态筛选
        """
        # 构建查询条件
        query = Product.filter(
            product_type=ProductType.VIP,
            is_deleted=BoolEnum.NO
        )
        
        # 关键词搜索（商品名称）
        if req.keyword:
            query = query.filter(name__icontains=req.keyword)
        
        # 状态筛选（is_published: True=已上架, False=未上架）
        if req.status is not None:
            is_published = bool(req.status)
            query = query.filter(is_published=is_published)
        
        # 查询所有符合条件的商品（不分页）
        select_fields = [
            "id", "name", "subtitle", "description",
            "is_published", "sort", "created_at", "updated_at"
        ]
        
        # 使用 values 方法直接获取字典列表
        products = await query.order_by("-sort", "-created_at").values(*select_fields)
        
        # 转换为列表
        items = list(products)
        
        # 关联查询 VIP 套餐信息
        if not items:
            return items

        # 获取商品ID列表
        product_ids = [item["id"] for item in items]
        
        # 批量查询 SKU 信息
        skus = await SKU.filter(product_id__in=product_ids).values("id", "product_id", "vip_plan_id")
        
        # 构建 product_id -> vip_plan_id 的映射
        product_vip_map = {}
        vip_plan_ids = set()
        for sku in skus:
            if sku.get("vip_plan_id"):
                product_vip_map[sku["product_id"]] = sku["vip_plan_id"]
                vip_plan_ids.add(sku["vip_plan_id"])
        
        if not vip_plan_ids:
            # 没有关联套餐，统一补 None
            for item in items:
                item["vip_plan_id"] = None
                item["vip_plan"] = None
            return items

        # 批量查询 VIP 套餐
        vip_plans = await VIPPlan.filter(id__in=vip_plan_ids)
        vip_plan_map = {plan.id: plan.to_dict() for plan in vip_plans}

        # 关联套餐信息到商品列表
        for item in items:
            vip_plan_id = product_vip_map.get(item["id"])
            item["vip_plan_id"] = vip_plan_id
            item["vip_plan"] = vip_plan_map.get(vip_plan_id)

        return items

    @atomic()
    async def create_vip_product(self, req: CreateVipProductReq):
        """
        新增VIP套餐商品
        1. 创建 VIP 套餐
        2. 创建商品并关联 VIP 套餐
        3. 创建商品 SKU
        """
        logger.info(f"开始新增VIP套餐商品: {req.name}")

        # 1. 创建 VIP 套餐
        vip_plan = VIPPlan(
            name=req.name,
            days=req.duration,
            price=req.price,
            privileges=req.privileges or req.description,  # 优先使用 privileges，如果没有则使用 description
        )
        vip_plan = await vip_plan_service.create_plan(vip_plan)
        logger.info(f"✅ 创建VIP套餐成功: {vip_plan.id}")

        # 2. 创建商品
        product = Product(
            name=req.name,
            subtitle=f"{req.duration}天VIP套餐",
            description=req.description,
            category_id=0,  # VIP商品默认分类为0
            series_id=0,  # VIP商品默认系列为0
            creator_user_id=0,  # 系统创建，用户ID为0
            product_type=ProductType.VIP,
            is_official=BoolEnum.YES,  # VIP套餐商品为自营商品
            check_state=ProductCheckState.APPROVED,  # 自营商品默认审核通过
            is_published=True,  # 默认上架
            sort=req.sort or 0,
        )
        product = await product_service.create(product)
        logger.info(f"✅ 创建VIP套餐商品成功: {product.id}")

        # 3. 创建 SKU（关联 VIP 套餐）
        sku = SKU(
            product_id=product.id,
            name=f"{req.name}",
            price=req.price,
            original_price=req.price,
            stock=999999,  # VIP商品库存设置为无限
            is_enabled=True,
            vip_plan_id=vip_plan.id,
        )
        await sku.save()
        logger.info(f"✅ 创建VIP套餐SKU成功: {sku.id}")

        # 删除VIP产品列表缓存
        await vip_product_service.invalidate_all_cache()
        logger.info(f"✅ 已清除VIP产品列表缓存（新增商品后）")

        return {
            "vip_plan_id": vip_plan.id,
            "product_id": product.id,
            "sku_id": sku.id,
        }

    @atomic()
    async def update_vip_product(self, req: UpdateVipProductReq):
        """
        修改VIP套餐商品
        1. 更新 VIP 套餐信息
        2. 更新商品信息
        3. 更新 SKU 信息
        """
        logger.info(f"开始修改VIP套餐商品: {req.vip_product_id}")

        # 1. 获取商品信息
        product = await product_service.get_by_id(req.vip_product_id)
        if not product:
            raise ValueError(f"商品 {req.vip_product_id} 不存在")

        # 1.1 获取商品关联的 SKU
        skus = await sku_service.get_skus_by_product_id(req.vip_product_id)
        if not skus:
            raise ValueError(f"商品 {req.vip_product_id} 没有关联的SKU")
        
        sku = skus[0]  # VIP商品通常只有一个SKU
        if not sku.vip_plan_id:
            raise ValueError(f"商品 {req.vip_product_id} 不是VIP套餐商品")

        # 2. 更新 VIP 套餐
        vip_plan_update_data = {}
        if req.name is not None:
            vip_plan_update_data["name"] = req.name
        if req.duration is not None:
            vip_plan_update_data["days"] = req.duration
        if req.price is not None:
            vip_plan_update_data["price"] = req.price
        if req.privileges is not None:
            vip_plan_update_data["privileges"] = req.privileges
        elif req.description is not None:
            # 如果没有 privileges，则使用 description 作为兼容
            vip_plan_update_data["privileges"] = req.description

        if vip_plan_update_data:
            await vip_plan_service.update_plan(sku.vip_plan_id, vip_plan_update_data)
            logger.info(f"✅ 更新VIP套餐成功: {sku.vip_plan_id}")

        # 3. 更新商品
        product_update_data = {}
        if req.name is not None:
            product_update_data["name"] = req.name
            product_update_data["subtitle"] = f"{req.duration or ''}天VIP套餐"
        if req.description is not None:
            product_update_data["description"] = req.description
        if req.sort is not None:
            product_update_data["sort"] = req.sort
        if req.status is not None:
            product_update_data["is_published"] = bool(req.status)

        if product_update_data:
            await product_service.update_by_id(req.vip_product_id, product_update_data)
            logger.info(f"✅ 更新商品成功: {req.vip_product_id}")

        # 4. 更新 SKU
        if req.price is not None:
            sku_update_data = {
                "price": req.price,
                "original_price": req.price,
            }
            await sku_service.update_by_id(sku.id, sku_update_data)
            logger.info(f"✅ 更新SKU成功: {sku.id}")

        # 删除VIP产品列表缓存
        await vip_product_service.invalidate_all_cache()
        logger.info(f"✅ 已清除VIP产品列表缓存（更新商品后）")

        logger.info(f"修改VIP套餐商品完成: {req.vip_product_id}")
        return True


vip_product_admin_service = VipProductAdminService()
