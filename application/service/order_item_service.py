from application.common.base import BaseService
from application.common.models import OrderItem


class OrderItemService(BaseService[OrderItem]):
    pass


order_item_service = OrderItemService()
