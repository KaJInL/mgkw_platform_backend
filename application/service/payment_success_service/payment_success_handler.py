from abc import ABC, abstractmethod

from application.apis.order.schema.response import OrderDetail
from application.common.models import OrderItem


class PaymentSuccessHandler(ABC):
    """
    支付成功处理接口
    """

    @abstractmethod
    async def handle(self, order_detail: OrderDetail, order_item: OrderItem):
        """
        处理支付成功业务逻辑

        :param order_item: 订单项详情
        :return: 是否处理成功
        """
