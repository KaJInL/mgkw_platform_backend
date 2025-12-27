from application.apis.order.schema.response import OrderDetail
from application.common.models import OrderItem
from application.service.payment_success_service.payment_success_handler import PaymentSuccessHandler


class PhysicalProductHandler(PaymentSuccessHandler):
    async def handle(self,order_detail : OrderDetail, order_item : OrderItem) :
        pass