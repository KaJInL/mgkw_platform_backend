from datetime import datetime

from application.common.models import OrderStatus
from application.core.redis_client import redis_client
from application.service.order_service import order_service
from application.core.logger_util import logger
from application.service.payment_success_service.design_product_handler import DesignProductHandler
from application.service.payment_success_service.physical_product_handler import PhysicalProductHandler
from application.service.payment_success_service.vip_product_handler import VipProductHandler


class PaymentSuccessService:
    """
    支付成功业务处理服务
    负责处理支付成功后的订单状态更新
    """

    def __init__(self):
        self._handlers = {
            "physical": PhysicalProductHandler(),
            "vip": VipProductHandler(),
            "design": DesignProductHandler()
        }

    async def on_payment_success(
            self,
            order_id: int,
            pay_time: datetime
    ) -> bool:
        """
        处理支付成功业务逻辑 - 更新订单状态为已支付

        :param order_id: 订单ID
        :param pay_time: 支付时间
        :return: 是否处理成功
        """
        try:
            logger.info(f"开始处理支付成功业务 - 订单ID: {order_id}, 支付时间: {pay_time}")
            # 获取订单信息
            order_detail = await order_service.get_order_detail(order_id)
            if order_detail.payment_type == OrderStatus.PAID:
                logger.warning(f"订单已支付 - 订单ID: {order_id}")
                return True

            # 更新订单状态为已支付
            success = await order_service.mark_order_as_paid(
                order_id=order_id,
                pay_time=pay_time
            )

            order_items = order_detail.items
            # 订单里面会有多个sku,使用不同的处理器进行处理
            for order_item in order_items:
                handler = self._handlers.get(order_item.item_type)
                await handler.handle(order_detail, order_item)

            if success:
                logger.info(f"✅ 支付成功业务处理完成 - 订单ID: {order_id}")
            else:
                logger.warning(f"⚠️ 订单状态更新失败 - 订单ID: {order_id}")
            return success

        except Exception as e:
            logger.exception(f"❌ 处理支付成功业务异常 - 订单ID: {order_id}, 错误: {e}")
            return False


# 创建服务实例
payment_success_service = PaymentSuccessService()

__all__ = [
    "payment_success_service"
]
