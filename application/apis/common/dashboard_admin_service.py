from datetime import datetime, timedelta
from application.common.base.base_service import CoreService
from application.common.models import User, Product, Design, Order
from application.apis.common.schema.response import DashboardStatsRes
from application.common.models.design import DesignState
from application.common.models.order import OrderStatus


class DashboardAdminService(CoreService):
    """
    首页统计 service
    """

    async def get_dashboard_stats(self) -> DashboardStatsRes:
        """
        获取首页统计数据
        :return: 统计数据
        """
        # 获取今天的开始时间
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 总用户数
        total_users = await User.all().count()
        
        # 今日新增用户数
        today_users = await User.filter(created_at__gte=today_start).count()
        
        # 总商品数（未删除的）
        total_products = await Product.filter(is_deleted="0").count()
        
        # 总设计作品数（未删除的）
        total_designs = await Design.filter(is_deleted="0").count()
        
        # 待审核设计作品数
        pending_designs = await Design.filter(
            is_deleted="0",
            state=DesignState.PENDING
        ).count()
        
        # 总订单数
        total_orders = await Order.all().count()
        
        # 今日订单数
        today_orders = await Order.filter(created_at__gte=today_start).count()
        
        # 今日收入（已支付的订单）
        today_paid_orders = await Order.filter(
            created_at__gte=today_start,
            status=OrderStatus.PAID
        ).all()
        today_revenue = sum(float(order.total_amount) for order in today_paid_orders)
        
        return DashboardStatsRes(
            total_users=total_users,
            total_products=total_products,
            total_designs=total_designs,
            total_orders=total_orders,
            today_users=today_users,
            today_orders=today_orders,
            today_revenue=today_revenue,
            pending_designs=pending_designs
        )


dashboard_admin_service = DashboardAdminService()

