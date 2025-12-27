from datetime import datetime, timedelta

from tortoise.transactions import atomic

from application.apis.order.schema.response import OrderDetail
from application.common.models import OrderItem, UserVIP
from application.core.lifespan import logger
from application.service.account_service import account_service
from application.service.payment_success_service.payment_success_handler import PaymentSuccessHandler
from application.service.product_service import product_service
from application.service.user_vip_service import user_vip_service
from application.service.vip_plan_service import vip_plan_service


class VipProductHandler(PaymentSuccessHandler):
    """
    VIP产品处理器
    """

    @atomic()
    async def handle(self, order_detail: OrderDetail, order_item: OrderItem):
        product = await product_service.get_by_id_with_skus(order_item.product_id)
        if not product:
            logger.error(f"商品不存在: {order_item.product_id}")
            return

        # 筛选出sku
        sku = next((item for item in product.skus if item.id == order_item.sku_id), None)
        if not sku or sku.vip_plan_id <= 0:
            logger.error(f"商品sku不存在: {order_item.sku_id}")
            return

        vip_plan = await vip_plan_service.get_by_id(sku.vip_plan_id)
        if not vip_plan:
            logger.error(f"会员套餐不存在: {sku.vip_plan_id}")
            return

        # 获取用户的vip记录,如果没有就创建
        user_vip = await user_vip_service.get_by_user_id(order_detail.user_id)
        now = datetime.now()

        if not user_vip:
            # 用户没有VIP记录，创建新记录
            user_vip = UserVIP(
                user_id=order_detail.user_id,
                total_days=vip_plan.days,
                start_time=now,
                end_time=now + timedelta(days=vip_plan.days)
            )
            await user_vip.save()
            logger.info(f"用户 {order_detail.user_id} 首次开通VIP，有效期 {vip_plan.days} 天")
        else:
            # 用户已有VIP记录，判断是续费还是重新开通
            if user_vip.end_time and user_vip.end_time > now:
                # VIP未过期，在原有基础上延长
                user_vip.total_days += vip_plan.days
                user_vip.end_time = user_vip.end_time + timedelta(days=vip_plan.days)
                logger.info(f"用户 {order_detail.user_id} VIP续费成功，延长 {vip_plan.days} 天")
            else:
                # VIP已过期，从当前时间重新计算
                user_vip.total_days += vip_plan.days
                user_vip.start_time = now
                user_vip.end_time = now + timedelta(days=vip_plan.days)
                logger.info(f"用户 {order_detail.user_id} VIP已过期，重新开通 {vip_plan.days} 天")

            await user_vip.save()
        await account_service.refresh_user_login_cache(order_detail.user_id)
        logger.info(
            f"VIP购买成功处理完成 - 用户: {order_detail.user_id}, 套餐: {vip_plan.name}, 天数: {vip_plan.days}, 累计天数: {user_vip.total_days}")
