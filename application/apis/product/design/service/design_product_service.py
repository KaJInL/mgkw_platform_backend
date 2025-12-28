from typing import List, Dict, Any

from application.service.account_service import account_service
from application.service.design_service import design_service
from application.service.product_service import product_service
from application.service.design_access_service import design_access_service
from application.service.user_design_license_service import user_design_license_service
from application.common.models.design import Design, DesignState
from application.common.models import UserDesignLicense
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
        # 检查用户是否为vip
        is_vip = await account_service.is_vip()

        # 检查设计作品是否存在且已通过审核
        if not design_info or design_info.state != DesignState.APPROVED:
            logger.warning(f"设计作品 {req.design_id} 不存在或未通过审核")
            raise ValueError("设计作品不存在或未通过审核")

        product_info = None
        if design_info.product_id:
            product_info = await product_service.get_by_id_with_skus(
                product_id=design_info.product_id
            )

        # 3. 检查是否有权限查看设计详情（resource_url和detail）
        if is_vip:
            has_permission = True
        else:
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

    async def get_purchased_design_products(
            self,
            user_id: int,
            page: int = 1,
            page_size: int = 10
    ):
        """
        获取用户已购买的设计作品商品列表（分页查询）
        
        :param user_id: 用户ID
        :param page: 页码，从1开始
        :param page_size: 每页数量
        :return: 分页数据 {list: [...], total: 0, hasNext: false}
        """
        # 1. 构建查询条件，使用 user_design_license_service 的分页方法
        query = UserDesignLicense.filter(user_id=user_id)

        # 2. 使用 paginate_dic 进行分页查询，只选择需要的字段
        pagination_result = await user_design_license_service.paginate_dic(
            query=query,
            page_no=page,
            page_size=page_size,
            select_fields=["design_id", "product_id"],
            order_by=["-created_at"]
        )

        license_list = pagination_result.get("list", [])
        if not license_list: return pagination_result

        # 3. 提取 design_id 列表（去重）并构建 design_id 到 product_id 的映射
        design_to_product_map = {}
        seen_design_ids = set()
        for license_item in license_list:
            design_id = license_item.get("design_id")
            if design_id and design_id not in seen_design_ids:
                seen_design_ids.add(design_id)
                design_to_product_map[design_id] = license_item.get("product_id")

        design_ids = list(design_to_product_map.keys())
        if not design_ids: return pagination_result

        # 4. 批量查询设计作品信息
        designs = await design_service.get_by_ids(design_ids)

        # 5. 构建返回结果
        result_list = []
        for design_dict in designs:
            design_id = design_dict.get("id")
            if not design_id or design_id not in design_to_product_map:
                continue

            title = design_dict.get("title", "")
            images = design_dict.get("images", [])
            product_id = design_to_product_map.get(design_id)

            # 获取第一张图片作为封面图
            img_url = images[0] if images and len(images) > 0 else None

            result_list.append({
                "img_url": img_url,
                "name": title,
                "product_id": product_id,
                "design_id": design_id
            })

        return {
            "list": result_list,
            "total": pagination_result.get("total", 0),
            "hasNext": pagination_result.get("hasNext", False)
        }


design_product_service = DesignProductService()
