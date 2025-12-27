from tortoise.transactions import atomic

from application.apis.order.schema.response import OrderDetail
from application.common.models import OrderItem
from application.core.lifespan import logger
from application.service.design_license_plan_service import design_license_plan_service
from application.service.payment_success_service.payment_success_handler import PaymentSuccessHandler
from application.service.product_service import product_service
from application.service.sku_service import sku_service
from application.service.user_design_license_service import user_design_license_service


class DesignProductHandler(PaymentSuccessHandler):
    @atomic()
    async def handle(self,order_detail : OrderDetail, order_item: OrderItem):
        product = await product_service.get_by_id_with_skus(order_item.product_id)
        if not product:
            logger.error(f"商品不存在: {order_item.product_id}")
            return

        # 筛选出sku
        sku = next((item for item in product.skus if item.id == order_item.sku_id), None)
        if not sku or  sku.design_license_plan_id <= 0:
            logger.error(f"商品sku不存在: {order_item.sku_id}")
            return

        # 获取授权plan
        license_plan = await design_license_plan_service.get_by_id(sku.design_license_plan_id)
        if not license_plan:
            logger.error(f"授权方案不存在: {sku.design_license_plan_id}")
            return

        # 给用户绑定授权方案
        await user_design_license_service.bind_license(order_detail.user_id,sku.design_id,license_plan)