# from typing import Optional
# from datetime import datetime
# from tortoise.expressions import Q
#
# from .schema.request import CreateProduct
# from application.common.constants import BoolEnum
# from application.common.exception.exception import HttpBusinessException
# from application.common.exception.http_error_code_enum import HttpErrorCodeEnum
# from application.common.models.product import Product, ProductCheckState
# from application.common.schema import LoginUserInfo
# from application.service.account_service import account_service
# from application.service.product_service import product_service
# from application.service.sku_service import sku_service
#
#
# class ProductAdminService:
#     """
#     产品管理后台服务
#     只包含有业务逻辑的方法，简单的 CRUD 操作直接在 API 层调用 product_service
#     """
#
#     async def create_product(self, req: CreateProductReq) -> Product:
#         """
#         创建商品（需要设置创建者ID和默认状态）
#
#         Args:
#             req: 商品创建请求对象
#
#         Returns:
#             创建的商品对象
#         """
#         login_user_info = await account_service.get_login_user_info()
#         user_id = login_user_info.user.id
#
#         # 准备数据并创建模型对象
#         data = req.model_dump(exclude_unset=True, by_alias=False)
#         product = Product(**data)
#         product.creator_user_id = user_id
#         product.check_state = ProductCheckState.PENDING  # 默认待审核
#         product.is_published = False  # 默认不上架
#
#         # 创建商品
#         product = await product_service.create(product)
#
#         return product
#
#     async def query_product_list(
#             self,
#             req: QueryProductListReq,
#             login_user_info: Optional[LoginUserInfo] = None
#     ) -> dict:
#         """
#         查询商品列表
#
#         Args:
#             req: 查询参数对象
#             login_user_info: 当前登录用户信息（可选，用于筛选创建者的商品）
#
#         Returns:
#             分页结果字典
#         """
#         # 构建查询
#         query = Product.filter(is_deleted=BoolEnum.NO)
#
#         # 审核状态筛选
#         if req.check_state:
#             query = query.filter(check_state=req.check_state)
#
#         # 商品类型筛选
#         if req.product_type:
#             query = query.filter(product_type=req.product_type)
#
#         # 是否上架筛选
#         if req.is_published is not None:
#             query = query.filter(is_published=req.is_published)
#
#         # 关键词搜索（名称或描述包含关键词）
#         if req.keyword:
#             query = query.filter(
#                 Q(name__icontains=req.keyword) | Q(description__icontains=req.keyword)
#             )
#
#         # 分页查询
#         result = await product_service.paginate(
#             query=query,
#             page_no=req.page,
#             page_size=req.page_size,
#             order_by=["-created_at"]
#         )
#
#         # 转换为字典以便添加 skus 字段
#         result_dict = result.to_dict()
#
#         if result_dict["list"]:
#             product_ids = [item["id"] for item in result_dict["list"]]
#
#             # 批量查询 SKU
#             skus = await sku_service.get_skus_by_product_ids(product_ids)
#
#             # 按 product_id 分组
#             sku_map = {}
#             for sku in skus:
#                 pid = sku.product_id
#                 if pid not in sku_map:
#                     sku_map[pid] = []
#                 sku_map[pid].append(sku.to_dict())
#
#             # 将 SKU 附加到商品列表
#             for item in result_dict["list"]:
#                 item["skus"] = sku_map.get(item["id"], [])
#
#         return result_dict
#
#     async def check_product(self, req: CheckProductReq) -> Product:
#         """
#         审核商品
#
#         Args:
#             req: 审核请求对象
#
#         Returns:
#             更新后的商品对象
#
#         Raises:
#             HttpBusinessException: 当商品不存在时
#         """
#         # 获取当前登录用户信息
#         login_user_info = await account_service.get_login_user_info()
#         checker_user_id = login_user_info.user.id
#
#         # 获取现有商品
#         existing = await product_service.get_by_id(req.product_id)
#         if not existing:
#             raise HttpBusinessException(
#                 HttpErrorCodeEnum.ERROR,
#                 "商品不存在"
#             )
#
#         # 准备更新数据
#         existing.check_state = req.check_state
#         existing.checker_user_id = checker_user_id
#         existing.checked_at = datetime.now()
#
#         if req.check_state == ProductCheckState.APPROVED:
#             existing.is_published = True
#
#
#         # 如果审核拒绝，需要填写拒绝原因
#         if req.check_state == ProductCheckState.REJECTED:
#             if not req.check_reason:
#                 raise HttpBusinessException(
#                     HttpErrorCodeEnum.ERROR,
#                     "审核拒绝时必须填写拒绝原因"
#                 )
#             existing.check_reason = req.check_reason
#         else:
#             # 审核通过时，清除拒绝原因
#             existing.check_reason = None
#
#         # 如果审核通过，自动上架
#         if req.check_state == ProductCheckState.APPROVED:
#             existing.is_published = True
#
#         # 更新商品
#         updated_count = await product_service.update_by_id(req.product_id, existing)
#
#         if updated_count == 0:
#             raise HttpBusinessException(
#                 HttpErrorCodeEnum.ERROR,
#                 "审核失败"
#             )
#
#         # 重新获取更新后的商品
#         product = await product_service.get_by_id(req.product_id)
#         return product
#
#
# # 创建全局实例
# product_admin_service = ProductAdminService()
