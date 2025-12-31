from tortoise.transactions import atomic
from typing import Optional, List
from application.service.design_service import design_service
from application.service.product_service import product_service
from application.service.sku_service import sku_service
from application.common.models.design import Design, DesignState
from application.common.models.product import Product, ProductCheckState
from application.common.constants import BoolEnum
from application.apis.product.schema.request import QueryDesignProductListReq, AuditDesignProductReq, GetDesignProductDetailReq, UpdateSkuReq
from application.apis.product.schema.response import ProductSimpleInfoRes
from application.core.logger_util import logger

class DesignProductAdminService:
    async def query_design_product_list(self, req: QueryDesignProductListReq):
        """
        查询设计作品商品列表
        """
        query = Design.filter(is_deleted=BoolEnum.NO)
        
        if req.keyword:
            query = query.filter(title__icontains=req.keyword)
            
        if req.state:
            query = query.filter(state=req.state)
            
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

    @atomic()
    async def audit_design_product(self, req: AuditDesignProductReq):
        """
        审核设计作品商品
        同步更新设计作品状态和关联商品的状态
        """
        logger.info(f"开始审核设计作品: {req.design_id}, 状态: {req.state}, 备注: {req.remark}")

        # 1. 获取设计作品
        design = await design_service.get_one(id=req.design_id, is_deleted=BoolEnum.NO)
        if not design:
            raise ValueError(f"设计作品 {req.design_id} 不存在")

        # 2. 更新设计作品状态
        old_state = design.state
        design.state = req.state
        await design.save()
        
        # 清除设计作品缓存
        await design_service.invalidate_cache(req.design_id, design.user_id)
        
        # 3. 同步更新关联商品状态
        if not design.product_id:
            logger.info(f"审核完成: 设计作品 {req.design_id} 状态由 {old_state} 变更为 {req.state} (无关联商品)")
            return True

        product = await product_service.get_by_id(design.product_id)
        if not product:
            logger.warning(f"设计作品 {req.design_id} 关联商品 {design.product_id} 不存在")
            # 即使关联商品不存在，设计作品状态已更新，仍视为操作成功
            return True

        product_check_state = ProductCheckState.PENDING
        is_published = False

        if req.state == DesignState.APPROVED:
            product_check_state = ProductCheckState.APPROVED
            is_published = True
        elif req.state == DesignState.REJECTED:
            product_check_state = ProductCheckState.REJECTED
            is_published = False
        
        # 更新商品状态
        update_data = {
            "check_state": product_check_state.value,
            "is_published": is_published,
            "check_reason": req.remark
        }
        
        await product_service.update_by_id(product.id, update_data)
        logger.info(f"同步更新关联商品 {product.id} 状态为 {product_check_state}")

        logger.info(f"审核完成: 设计作品 {req.design_id} 状态由 {old_state} 变更为 {req.state}")
        return True

    async def get_design_product_detail(self, req: GetDesignProductDetailReq):
        """
        获取设计作品商品详情
        """
        # 1. 获取 Design 详情（包含已删除的）
        design_info = await design_service.get_by_id_with_cache(
            design_id=req.design_id,
            include_deleted=True
        )
        
        product_info = None
        if design_info and design_info.product_id:
             # 2. 获取 Product 详情 (包含SKU)
             product_info = await product_service.get_by_id_with_skus(
                 product_id=design_info.product_id
             )

        # 确保返回的是字典而不是 Tortoise 模型对象
        return {
            "design": design_info.to_dict() if design_info else None,
            "product": product_info.model_dump() if product_info else None
        }

    @atomic()
    async def update_sku(self, req: UpdateSkuReq):
        """
        更新 SKU 价格
        """
        logger.info(f"开始更新 SKU 价格: {req.sku_id}, 新价格: {req.price}")

        # 1. 获取 SKU
        sku = await sku_service.get_by_id(req.sku_id)
        if not sku:
            raise ValueError(f"SKU {req.sku_id} 不存在")

        # 2. 更新价格
        update_data = {"price": req.price}
        await sku_service.update_by_id(req.sku_id, update_data)
        
        # 3. 清除关联商品的缓存
        await product_service.invalidate_cache(sku.product_id)
        
        logger.info(f"更新 SKU {req.sku_id} 价格完成: {req.price}")
        return True

    async def search_product_by_keyword(
        self, 
        keyword: Optional[str] = None,
        page_no: int = 1,
        page_size: int = 10
    ) -> List[ProductSimpleInfoRes]:
        """
        搜索商品（仅返回id、封面图片、名称）
        
        :param keyword: 搜索关键词
        :param page_no: 页码
        :param page_size: 每页数量
        :return: 商品简单信息列表
        """
        # 构建查询条件：只查询未删除的商品
        query = Product.filter(is_deleted=BoolEnum.NO)
        
        # 如果有关键词，进行模糊搜索
        if keyword:
            query = query.filter(name__icontains=keyword)
        
        # 分页查询，只选择需要的字段
        select_fields = ["id", "cover_image", "name"]
        
        # 使用 product_service 的分页方法
        pagination_result = await product_service.paginate_dic(
            query=query,
            page_no=page_no,
            page_size=page_size,
            select_fields=select_fields,
            order_by=["-created_at"]
        )
        
        # 转换为 ProductSimpleInfoRes 列表
        product_list = pagination_result.get("list", [])
        result = [ProductSimpleInfoRes(**item) for item in product_list]
        
        return result

design_product_admin_service = DesignProductAdminService()
